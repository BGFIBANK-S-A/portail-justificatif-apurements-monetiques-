import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apurement.models import Utilisateur
from apurement.serializers import UtilisateurSerializer
from apurement.services.journal import journaliser
from apurement.services.notifications import envoyer_email

TENTATIVES_MAX = 5
VERROUILLAGE_MINUTES = 15


def _jetons_pour(utilisateur):
    refresh = RefreshToken.for_user(utilisateur)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        mot_de_passe = request.data.get("mot_de_passe") or request.data.get("password") or ""

        utilisateur = Utilisateur.objects.filter(email=email).first()
        if not utilisateur:
            return Response({"detail": "Email ou mot de passe incorrect."}, status=401)

        if utilisateur.verrouille_jusqua and utilisateur.verrouille_jusqua > timezone.now():
            return Response({"detail": "Compte temporairement verrouille suite a plusieurs echecs. Reessayez plus tard."}, status=423)

        if not utilisateur.actif:
            return Response({"detail": "Compte inactif. Utilisez le lien recu par email pour l'activer."}, status=403)

        if utilisateur.suspendu:
            return Response({"detail": "Compte suspendu. Contactez votre agence."}, status=403)

        if not utilisateur.check_password(mot_de_passe):
            utilisateur.tentatives_echouees += 1
            if utilisateur.tentatives_echouees >= TENTATIVES_MAX:
                utilisateur.verrouille_jusqua = timezone.now() + timedelta(minutes=VERROUILLAGE_MINUTES)
            utilisateur.save()
            return Response({"detail": "Email ou mot de passe incorrect."}, status=401)

        utilisateur.tentatives_echouees = 0
        utilisateur.verrouille_jusqua = None
        utilisateur.save()
        journaliser("connexion", f"Connexion de {utilisateur.email}", utilisateur)

        return Response({**_jetons_pour(utilisateur), "utilisateur": UtilisateurSerializer(utilisateur).data})


class MoiView(APIView):
    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)


class ActivationView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, token):
        utilisateur = Utilisateur.objects.filter(token_activation=token).first()
        if not utilisateur or (utilisateur.token_activation_expire and utilisateur.token_activation_expire < timezone.now()):
            return Response({"detail": "Lien d'activation invalide ou expire."}, status=404)
        return Response({"email": utilisateur.email})

    def post(self, request, token):
        utilisateur = Utilisateur.objects.filter(token_activation=token).first()
        if not utilisateur or (utilisateur.token_activation_expire and utilisateur.token_activation_expire < timezone.now()):
            return Response({"detail": "Lien d'activation invalide ou expire."}, status=404)

        mot_de_passe = request.data.get("mot_de_passe") or ""
        confirmation = request.data.get("confirmation") or ""
        if len(mot_de_passe) < 6:
            return Response({"detail": "6 caracteres minimum."}, status=400)
        if mot_de_passe != confirmation:
            return Response({"detail": "Les mots de passe ne correspondent pas."}, status=400)

        utilisateur.set_password(mot_de_passe)
        utilisateur.actif = True
        utilisateur.token_activation = None
        utilisateur.token_activation_expire = None
        utilisateur.save()
        journaliser("activation_compte", f"Activation du compte {utilisateur.email}", utilisateur)
        return Response({**_jetons_pour(utilisateur), "utilisateur": UtilisateurSerializer(utilisateur).data})


class DemandeReinitialisationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        utilisateur = Utilisateur.objects.filter(email=email, actif=True).first()
        # Reponse identique que le compte existe ou non : on ne revele pas
        # l'existence d'un compte a un email donne.
        if utilisateur:
            utilisateur.token_reinitialisation = secrets.token_urlsafe(24)
            utilisateur.token_reinitialisation_expire = timezone.now() + timedelta(hours=2)
            utilisateur.save()
            lien = f"{settings.FRONTEND_URL}/reinitialiser/{utilisateur.token_reinitialisation}"
            corps = (
                f"Bonjour {utilisateur.prenom},\n\nVous avez demande la reinitialisation de votre mot de passe. "
                f"Ce lien est valable 2 heures :\n{lien}\n\nSi vous n'etes pas a l'origine de cette demande, ignorez cet email.\n\n"
                "Cordialement,\nBGFIBank Gabon"
            )
            try:
                envoyer_email(utilisateur.email, "Reinitialisation de votre mot de passe", corps)
            except Exception as e:
                journaliser("erreur_notification", f"Echec envoi reinitialisation a {utilisateur.email} : {e}")
        return Response({"detail": "Si un compte existe pour cet email, un lien de reinitialisation a ete envoye."})


class ConfirmerReinitialisationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, token):
        utilisateur = Utilisateur.objects.filter(token_reinitialisation=token).first()
        if not utilisateur or (utilisateur.token_reinitialisation_expire and utilisateur.token_reinitialisation_expire < timezone.now()):
            return Response({"detail": "Lien invalide ou expire."}, status=404)

        mot_de_passe = request.data.get("mot_de_passe") or ""
        confirmation = request.data.get("confirmation") or ""
        if len(mot_de_passe) < 6:
            return Response({"detail": "6 caracteres minimum."}, status=400)
        if mot_de_passe != confirmation:
            return Response({"detail": "Les mots de passe ne correspondent pas."}, status=400)

        utilisateur.set_password(mot_de_passe)
        utilisateur.token_reinitialisation = None
        utilisateur.token_reinitialisation_expire = None
        utilisateur.tentatives_echouees = 0
        utilisateur.verrouille_jusqua = None
        utilisateur.save()
        journaliser("reinitialisation_mot_de_passe", f"Mot de passe reinitialise pour {utilisateur.email}", utilisateur)
        return Response({"detail": "Mot de passe reinitialise."})


class RenvoyerActivationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        utilisateur = Utilisateur.objects.filter(email=email, actif=False).first()
        if utilisateur:
            if not utilisateur.token_activation:
                utilisateur.token_activation = secrets.token_urlsafe(24)
            utilisateur.token_activation_expire = timezone.now() + timedelta(days=settings.ACTIVATION_DUREE_VALIDITE_JOURS)
            utilisateur.save()
            lien = f"{settings.FRONTEND_URL}/activer/{utilisateur.token_activation}"
            corps = (
                f"Bonjour {utilisateur.prenom},\n\nVoici votre lien d'activation "
                f"(valable {settings.ACTIVATION_DUREE_VALIDITE_JOURS} jours) :\n{lien}\n\nCordialement,\nBGFIBank Gabon"
            )
            try:
                envoyer_email(utilisateur.email, "Votre lien d'acces au Portail Justificatif d'Apurement", corps)
            except Exception as e:
                journaliser("erreur_notification", f"Echec renvoi activation a {utilisateur.email} : {e}")
        return Response({"detail": "Si un compte existe pour cet email, un lien a ete envoye."})
