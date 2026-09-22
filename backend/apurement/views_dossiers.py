import mimetypes
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apurement.models import Dossier, Document
from apurement.permissions import EstPersonnelBanque, autorise_dossier
from apurement.serializers import DossierDetailSerializer, DossierListeSerializer
from apurement.services.crypto import est_image, extension_valide, lire_fichier_dechiffre, sauvegarder_fichier_chiffre
from apurement.services.dossiers import recalculer_statut
from apurement.services.journal import journaliser

TYPES_DOC_VOYAGE = ("passeport", "billet_aller", "billet_retour", "visa", "autre_justificatif")


def _chemin_dossier_upload(client_id, reference):
    chemin = os.path.join(settings.MEDIA_ROOT, f"client_{client_id}", reference)
    os.makedirs(chemin, exist_ok=True)
    return chemin


class DashboardView(APIView):
    def get(self, request):
        tous = Dossier.objects.filter(client=request.user).order_by("-date_creation")
        dossiers = [d for d in tous if d.statut not in ("valide", "refuse")]
        archives = [d for d in tous if d.statut in ("valide", "refuse")]
        return Response({
            "dossiers": DossierListeSerializer(dossiers, many=True).data,
            "archives": DossierListeSerializer(archives, many=True).data,
        })


class AnticiperVoyageView(APIView):
    def post(self, request):
        annee = datetime.now().year
        ref = f"DOC-{annee}-VY{uuid.uuid4().hex[:5].upper()}"
        dossier = Dossier.objects.create(
            reference=ref, type_dossier="voyage", statut="incomplet", montant=0.0, client=request.user,
        )
        journaliser("creation_dossier_anticipe", f"Voyage anticipe cree : {ref}", request.user)
        return Response(DossierDetailSerializer(dossier).data, status=201)


class DossierDetailView(APIView):
    def get(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).select_related("client").first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if dossier.client_id != request.user.id and not (EstPersonnelBanque().has_permission(request, self) and autorise_dossier(request.user, dossier)):
            return Response({"detail": "Non autorise."}, status=403)
        return Response(DossierDetailSerializer(dossier).data)


class UploadDocumentView(APIView):
    def post(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if dossier.client_id != request.user.id or dossier.statut not in ("incomplet", "en_attente", "en_cours"):
            return Response({"erreur": "Non autorise."}, status=403)

        champ = request.data.get("type_document")
        fichier = request.FILES.get("file")

        if not fichier or not extension_valide(fichier.name):
            return Response({"erreur": "Fichier invalide ou format non supporte."}, status=400)
        if fichier.size > settings.MAX_UPLOAD_SIZE:
            return Response({"erreur": "Fichier trop volumineux (5 Mo maximum)."}, status=400)
        if champ not in TYPES_DOC_VOYAGE:
            return Response({"erreur": "Type de document invalide."}, status=400)

        repertoire = _chemin_dossier_upload(dossier.client_id, dossier.reference)
        par_type = {d.type_document: d for d in dossier.documents.filter(ligne__isnull=True)}

        if champ in par_type:
            ancien = par_type[champ]
            try:
                os.remove(ancien.chemin)
            except OSError:
                pass
            ancien.delete()

        nom_sur_disque = f"{champ}_{uuid.uuid4().hex[:8]}_{fichier.name}"
        chemin = os.path.join(repertoire, nom_sur_disque)
        sauvegarder_fichier_chiffre(fichier, chemin)

        Document.objects.create(nom_fichier=fichier.name, type_document=champ, chemin=chemin, dossier=dossier)
        dossier.a_ete_mis_a_jour = True
        recalculer_statut(dossier)
        dossier.date_mise_a_jour = timezone.now()
        dossier.save()

        return Response(DossierDetailSerializer(dossier).data)


class JustifierLignesView(APIView):
    def post(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if dossier.client_id != request.user.id or dossier.statut not in ("incomplet", "en_attente", "en_cours"):
            return Response({"detail": "Non autorise."}, status=403)

        if dossier.type_dossier == "voyage" and not (dossier.date_debut_voyage and dossier.date_fin_voyage):
            date_aller = request.data.get("date_aller_manuelle")
            date_retour = request.data.get("date_retour_manuelle")
            if date_aller:
                try:
                    dossier.date_debut_voyage = datetime.strptime(date_aller, "%Y-%m-%d")
                    dossier.periode = dossier.date_debut_voyage.strftime("%Y-%m")
                except ValueError:
                    pass
            if date_retour:
                try:
                    dossier.date_fin_voyage = datetime.strptime(date_retour, "%Y-%m-%d")
                except ValueError:
                    pass

        repertoire = _chemin_dossier_upload(dossier.client_id, dossier.reference)
        maj = False

        for ligne in dossier.lignes.all():
            fichier = request.FILES.get(f"justif_{ligne.id}")
            if not fichier or not extension_valide(fichier.name):
                continue
            for ancien in ligne.justificatifs.all():
                try:
                    os.remove(ancien.chemin)
                except OSError:
                    pass
                ancien.delete()
            type_choisi = request.data.get(f"type_justif_{ligne.id}") or "justificatif"
            nom_sur_disque = f"justif_ligne{ligne.id}_{uuid.uuid4().hex[:8]}_{fichier.name}"
            chemin = os.path.join(repertoire, nom_sur_disque)
            sauvegarder_fichier_chiffre(fichier, chemin)
            Document.objects.create(
                nom_fichier=fichier.name, type_document=type_choisi, chemin=chemin, dossier=dossier, ligne=ligne,
            )
            maj = True

        if maj:
            dossier.a_ete_mis_a_jour = True
        recalculer_statut(dossier)
        dossier.date_mise_a_jour = timezone.now()
        dossier.save()

        return Response(DossierDetailSerializer(dossier).data)


class AnnulerDossierView(APIView):
    def post(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if dossier.client_id != request.user.id:
            return Response({"detail": "Non autorise."}, status=403)
        if dossier.lignes.exists() or dossier.documents.exists():
            return Response({"detail": "Ce dossier contient deja des elements, impossible de le supprimer."}, status=400)
        dossier.delete()
        return Response(status=204)


class VoirDocumentView(APIView):
    def get(self, request, document_id):
        doc = Document.objects.filter(id=document_id).select_related("dossier").first()
        if not doc:
            return Response({"detail": "Introuvable."}, status=404)
        if doc.dossier.client_id != request.user.id and not (EstPersonnelBanque().has_permission(request, self) and autorise_dossier(request.user, doc.dossier)):
            return Response({"detail": "Non autorise."}, status=403)
        if not os.path.exists(doc.chemin):
            return HttpResponseNotFound("Fichier introuvable")
        contenu = lire_fichier_dechiffre(doc.chemin)
        type_mime = mimetypes.guess_type(doc.nom_fichier)[0] or "application/octet-stream"
        reponse = HttpResponse(contenu, content_type=type_mime)
        reponse["Content-Disposition"] = f'inline; filename="{doc.nom_fichier}"'
        return reponse
