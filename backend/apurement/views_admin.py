import os
import uuid

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db.models import Count
from django.utils import timezone
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apurement.models import Agence, Dossier, Document, JournalEvenement, Utilisateur
from apurement.permissions import EstAdmin, EstPersonnelBanque, EstSuperviseurOuAdmin, autorise_dossier, filtrer_dossiers_actionnables
from apurement.serializers import DossierDetailSerializer, DossierListeSerializer, UtilisateurSerializer
from apurement.services.dossiers import recalculer_statut
from apurement.services.imports import importer_fichier, importer_portefeuille
from apurement.services.journal import journaliser

STATUTS_ARCHIVES = ("valide", "refuse")


class AdminDashboardView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def get(self, request):
        f_statut = request.query_params.get("statut", "")
        f_type = request.query_params.get("type", "")

        base = Dossier.objects.exclude(statut__in=STATUTS_ARCHIVES)
        if request.user.role == "crc":
            base = base.filter(client__crc=request.user)
        elif request.user.role == "acrc":
            base = base.filter(client__crc__in=request.user.crcs_assistes.all())

        if f_statut:
            base = base.filter(statut=f_statut)
        if f_type:
            base = base.filter(type_dossier=f_type)

        tous = Dossier.objects.exclude(statut__in=STATUTS_ARCHIVES)
        if request.user.role == "crc":
            tous = tous.filter(client__crc=request.user)
        elif request.user.role == "acrc":
            tous = tous.filter(client__crc__in=request.user.crcs_assistes.all())

        stats = {
            "actifs": tous.count(),
            "incomplets": tous.filter(statut="incomplet").count(),
            "en_attente": tous.filter(statut="en_attente").count(),
            "en_cours": tous.filter(statut="en_cours").count(),
            "mises_en_demeure": tous.exclude(date_mise_en_demeure=None).count(),
            "suspendus": Utilisateur.objects.filter(role="client", suspendu=True).count(),
        }
        return Response({
            "dossiers": DossierListeSerializer(base.order_by("-date_creation"), many=True).data,
            "stats": stats,
        })


class AdminArchiveView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def get(self, request):
        fins = Dossier.objects.filter(statut__in=STATUTS_ARCHIVES).select_related("client").order_by("-date_mise_a_jour")
        if request.user.role == "crc":
            fins = fins.filter(client__crc=request.user)
        elif request.user.role == "acrc":
            fins = fins.filter(client__crc__in=request.user.crcs_assistes.all())

        par_client = {}
        for d in fins:
            entree = par_client.setdefault(d.client_id, {"client": d.client, "dossiers": []})
            entree["dossiers"].append(d)

        groupes = [
            {"client": UtilisateurSerializer(g["client"]).data, "dossiers": DossierListeSerializer(g["dossiers"], many=True).data}
            for g in sorted(par_client.values(), key=lambda g: g["client"].nom)
        ]
        return Response({"groupes": groupes, "total": fins.count()})


class AdminDossierDetailView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def get(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).select_related("client").first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if not autorise_dossier(request.user, dossier):
            return Response({"detail": "Non autorise."}, status=403)
        if dossier.a_ete_mis_a_jour:
            dossier.a_ete_mis_a_jour = False
            dossier.save()
        return Response(DossierDetailSerializer(dossier).data)


class AdminDecisionDossierView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def post(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if not autorise_dossier(request.user, dossier):
            return Response({"detail": "Non autorise."}, status=403)

        action = request.data.get("action")
        commentaire = (request.data.get("commentaire") or "").strip()

        if action in ("refuser", "demander_complement") and not commentaire:
            return Response({"detail": "Un motif est obligatoire pour cette action."}, status=400)

        if action == "prendre_en_charge":
            dossier.statut = "en_cours"
            dossier.pris_en_charge_par = request.user
        elif action == "valider":
            dossier.statut = "valide"
        elif action == "refuser":
            dossier.statut = "refuse"
        elif action == "demander_complement":
            dossier.statut = "incomplet"
            dossier.complement_demande_le = timezone.now()
        else:
            return Response({"detail": "Action inconnue."}, status=400)

        if commentaire:
            dossier.commentaire_admin = commentaire
        dossier.save()
        journaliser(f"decision_dossier_{action}", f"Dossier {dossier.reference} : {action}", request.user)
        return Response(DossierDetailSerializer(dossier).data)


class AdminDocumentDecisionView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def post(self, request, document_id):
        doc = Document.objects.filter(id=document_id).select_related("dossier").first()
        if not doc:
            return Response({"detail": "Introuvable."}, status=404)
        if not autorise_dossier(request.user, doc.dossier):
            return Response({"detail": "Non autorise."}, status=403)

        action = request.data.get("action")
        if action == "valider":
            doc.statut, doc.motif_refus = "valide", None
        else:
            doc.statut = "refuse"
            doc.motif_refus = (request.data.get("motif_refus") or "").strip() or "Non conforme"
        doc.save()

        recalculer_statut(doc.dossier)
        doc.dossier.save()
        return Response(DossierDetailSerializer(doc.dossier).data)


class AdminSupprimerDossierView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def post(self, request, dossier_id):
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"detail": "Introuvable."}, status=404)
        if not autorise_dossier(request.user, dossier):
            return Response({"detail": "Non autorise."}, status=403)
        repertoire = os.path.join(settings.MEDIA_ROOT, f"client_{dossier.client_id}", dossier.reference)
        for doc in dossier.documents.all():
            try:
                os.remove(doc.chemin)
            except OSError:
                pass
        try:
            os.rmdir(repertoire)
        except OSError:
            pass
        journaliser("suppression_dossier", f"Dossier {dossier.reference} supprime", request.user)
        dossier.delete()
        return Response(status=204)


class AdminImportFichierView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)
    parser_classes = (MultiPartParser,)

    def post(self, request):
        fichier = request.FILES.get("fichier")
        if not fichier or not fichier.name.endswith((".xlsx", ".xls", ".csv")):
            return Response({"erreur": "Fichier non pris en charge (xlsx, xls ou csv attendu)."}, status=400)

        repertoire = os.path.join(settings.MEDIA_ROOT, "_imports")
        os.makedirs(repertoire, exist_ok=True)
        chemin = os.path.join(repertoire, f"{uuid.uuid4().hex[:8]}_{fichier.name}")
        with open(chemin, "wb") as f:
            for morceau in fichier.chunks():
                f.write(morceau)

        try:
            resume = importer_fichier(chemin, base_url=request.data.get("base_url"))
        except ValueError as e:
            return Response({"erreur": str(e)}, status=400)
        except Exception as e:
            return Response({"erreur": f"Erreur import : {e}"}, status=400)

        journaliser("import_fichier_journalier", f"{resume.get('lignes', 0)} ligne(s) importee(s)", request.user)
        return Response(resume)


class AdminImportPortefeuilleView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)
    parser_classes = (MultiPartParser,)

    def post(self, request):
        fichier = request.FILES.get("fichier")
        if not fichier or not fichier.name.endswith((".xlsx", ".xls", ".csv")):
            return Response({"erreur": "Fichier non pris en charge (xlsx, xls ou csv attendu)."}, status=400)

        repertoire = os.path.join(settings.MEDIA_ROOT, "_imports")
        os.makedirs(repertoire, exist_ok=True)
        chemin = os.path.join(repertoire, f"{uuid.uuid4().hex[:8]}_{fichier.name}")
        with open(chemin, "wb") as f:
            for morceau in fichier.chunks():
                f.write(morceau)

        try:
            resume = importer_portefeuille(chemin)
        except ValueError as e:
            return Response({"erreur": str(e)}, status=400)
        except Exception as e:
            return Response({"erreur": f"Erreur import : {e}"}, status=400)

        journaliser("import_portefeuille", f"{resume.get('clients_relies', 0)} client(s) relie(s)", request.user)
        return Response(resume)


class AdminUtilisateursView(APIView):
    permission_classes = (EstAdmin,)

    def get(self, request):
        admins = Utilisateur.objects.filter(role__in=("admin", "superviseur"))
        return Response({
            "admins": UtilisateurSerializer(admins, many=True).data,
            "nb_clients": Utilisateur.objects.filter(role="client").count(),
        })

    def post(self, request):
        nom = (request.data.get("nom") or "").strip()
        prenom = (request.data.get("prenom") or "").strip()
        email = (request.data.get("email") or "").strip().lower()
        role = request.data.get("role") or "admin"
        mot_de_passe = request.data.get("mot_de_passe") or ""

        if not nom or not prenom or not email:
            return Response({"detail": "Nom, prenom et email sont obligatoires."}, status=400)
        if len(mot_de_passe) < 6:
            return Response({"detail": "Le mot de passe doit contenir au moins 6 caracteres."}, status=400)
        if Utilisateur.objects.filter(email=email).exists():
            return Response({"detail": "Un compte existe deja avec cet email."}, status=400)
        if role not in ("admin", "superviseur"):
            return Response({"detail": "Role invalide."}, status=400)

        utilisateur = Utilisateur.objects.create(
            nom=nom, prenom=prenom, email=email, password=make_password(mot_de_passe),
            actif=True, role=role, is_staff=True,
        )
        journaliser("creation_compte_personnel", f"{role} cree : {utilisateur.email}", request.user)
        return Response(UtilisateurSerializer(utilisateur).data, status=201)


def _nb_admins_actifs():
    return Utilisateur.objects.filter(role="admin", actif=True).count()


class AdminBasculerUtilisateurView(APIView):
    permission_classes = (EstAdmin,)

    def post(self, request, utilisateur_id):
        cible = Utilisateur.objects.filter(id=utilisateur_id).first()
        if not cible:
            return Response({"detail": "Introuvable."}, status=404)
        if cible.role not in ("admin", "superviseur"):
            return Response({"detail": "Action reservee au personnel."}, status=400)
        if cible.id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas modifier votre propre compte."}, status=400)
        if cible.actif and cible.role == "admin" and _nb_admins_actifs() <= 1:
            return Response({"detail": "Impossible : il doit rester au moins un administrateur actif."}, status=400)

        cible.actif = not cible.actif
        cible.save()
        return Response(UtilisateurSerializer(cible).data)


class AdminSupprimerUtilisateurView(APIView):
    permission_classes = (EstAdmin,)

    def post(self, request, utilisateur_id):
        cible = Utilisateur.objects.filter(id=utilisateur_id).first()
        if not cible:
            return Response({"detail": "Introuvable."}, status=404)
        if cible.role not in ("admin", "superviseur"):
            return Response({"detail": "Action reservee au personnel."}, status=400)
        if cible.id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas supprimer votre propre compte."}, status=400)
        if cible.actif and cible.role == "admin" and _nb_admins_actifs() <= 1:
            return Response({"detail": "Impossible : il doit rester au moins un administrateur actif."}, status=400)
        cible.delete()
        return Response(status=204)


class AdminSuspendusView(APIView):
    permission_classes = (EstPersonnelBanque,)

    def get(self, request):
        suspendus = Utilisateur.objects.filter(role="client", suspendu=True).order_by("-date_suspension")
        return Response(UtilisateurSerializer(suspendus, many=True).data)


class AdminReactiverClientView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)

    def post(self, request, utilisateur_id):
        client = Utilisateur.objects.filter(id=utilisateur_id, role="client").first()
        if not client:
            return Response({"detail": "Introuvable."}, status=404)
        client.suspendu = False
        client.date_suspension = None
        client.motif_suspension = None
        client.save()
        journaliser("reactivation_client", f"Client {client.email} reactive", request.user)
        return Response(UtilisateurSerializer(client).data)


class JournalView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)

    def get(self, request):
        evenements = JournalEvenement.objects.select_related("utilisateur").all()[:200]
        return Response([
            {
                "id": e.id,
                "date_evenement": e.date_evenement,
                "type_action": e.type_action,
                "description": e.description,
                "role_acteur": e.role_acteur,
                "utilisateur": f"{e.utilisateur.prenom} {e.utilisateur.nom}" if e.utilisateur else None,
            }
            for e in evenements
        ])


class CrcArborescenceView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)

    def get(self, request):
        crcs = list(Utilisateur.objects.filter(role="crc").select_related("agence"))
        crc_ids = [c.id for c in crcs]

        nb_en_attente_par_crc = {}
        if crc_ids:
            base = filtrer_dossiers_actionnables(Dossier.objects.filter(client__crc_id__in=crc_ids))
            for crc_id in crc_ids:
                nb_en_attente_par_crc[crc_id] = base.filter(client__crc_id=crc_id).count()

        nb_clients_par_crc = {}
        if crc_ids:
            for ligne in Utilisateur.objects.filter(role="client", crc_id__in=crc_ids).values("crc_id").annotate(n=Count("id")):
                nb_clients_par_crc[ligne["crc_id"]] = ligne["n"]

        par_agence = {}
        for crc in crcs:
            cle = crc.agence_id or 0
            groupe = par_agence.setdefault(cle, {"id": cle, "nom": crc.agence.nom if crc.agence else "Sans agence", "crcs": []})
            groupe["crcs"].append({
                "id": crc.id, "nom": crc.nom, "prenom": crc.prenom, "email": crc.email, "actif": crc.actif,
                "nb_en_attente": nb_en_attente_par_crc.get(crc.id, 0),
                "nb_clients": nb_clients_par_crc.get(crc.id, 0),
            })

        groupes = sorted(par_agence.values(), key=lambda g: (g["id"] == 0, g["nom"]))
        return Response({"groupes": groupes})


class CrcDossiersEnAttenteView(APIView):
    permission_classes = (EstSuperviseurOuAdmin,)

    def get(self, request, crc_id):
        crc = Utilisateur.objects.filter(id=crc_id, role="crc").first()
        if not crc:
            return Response({"detail": "Introuvable."}, status=404)
        dossiers = filtrer_dossiers_actionnables(
            Dossier.objects.filter(client__crc=crc).select_related("client")
        ).order_by("-date_creation")
        return Response({
            "crc": UtilisateurSerializer(crc).data,
            "dossiers": DossierListeSerializer(dossiers, many=True).data,
        })
