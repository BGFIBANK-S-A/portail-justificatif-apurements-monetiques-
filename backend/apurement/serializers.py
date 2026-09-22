from rest_framework import serializers

from apurement.models import Agence, Dossier, Document, LigneTransaction, Utilisateur
from apurement.services.dossiers import (
    jours_restants_justification,
    montant_justifie,
    preuve_voyage_manquante,
    detecter_incoherences,
)


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = (
            "id", "nom", "prenom", "email", "role", "actif", "suspendu",
            "code_client", "code_gestionnaire", "telephone", "date_creation",
            "motif_suspension", "date_suspension",
        )


class AgenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agence
        fields = ("id", "nom", "code_agence")


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ("id", "nom_fichier", "type_document", "statut", "motif_refus", "date_upload", "ligne")


class LigneTransactionSerializer(serializers.ModelSerializer):
    est_justifiee = serializers.BooleanField(read_only=True)
    justificatifs = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = LigneTransaction
        fields = (
            "id", "date_operation", "libelle", "montant", "devise",
            "hors_plafond", "est_justifiee", "justificatifs",
        )


class DossierListeSerializer(serializers.ModelSerializer):
    client = UtilisateurSerializer(read_only=True)
    jours_restants = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = (
            "id", "reference", "type_dossier", "periode", "montant", "statut",
            "client", "jours_restants", "date_creation", "date_mise_a_jour",
        )

    def get_jours_restants(self, obj):
        return jours_restants_justification(obj)


class DossierDetailSerializer(serializers.ModelSerializer):
    client = UtilisateurSerializer(read_only=True)
    lignes = LigneTransactionSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    montant_justifie = serializers.SerializerMethodField()
    jours_restants = serializers.SerializerMethodField()
    modifiable = serializers.SerializerMethodField()
    preuve_voyage_manquante = serializers.SerializerMethodField()
    incoherences = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = (
            "id", "reference", "type_dossier", "periode", "montant", "statut",
            "date_debut_voyage", "date_fin_voyage", "commentaire_admin",
            "date_creation", "date_mise_a_jour", "client", "lignes", "documents",
            "montant_justifie", "jours_restants", "modifiable",
            "preuve_voyage_manquante", "incoherences",
        )

    def get_montant_justifie(self, obj):
        return montant_justifie(obj)

    def get_jours_restants(self, obj):
        return jours_restants_justification(obj)

    def get_modifiable(self, obj):
        return obj.statut in ("incomplet", "en_attente", "en_cours")

    def get_preuve_voyage_manquante(self, obj):
        return preuve_voyage_manquante(obj)

    def get_incoherences(self, obj):
        return detecter_incoherences(obj)
