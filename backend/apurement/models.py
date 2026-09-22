from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class Agence(models.Model):
    nom = models.CharField(max_length=200, unique=True)
    code_agence = models.CharField(max_length=30, unique=True, null=True, blank=True)

    class Meta:
        db_table = "agence"

    def __str__(self):
        return self.nom


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        utilisateur = self.model(email=self.normalize_email(email), **extra_fields)
        if password:
            utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("actif", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ("admin", "Administrateur"),
        ("superviseur", "Superviseur"),
        ("crc", "CRC"),
        ("acrc", "ACRC"),
        ("client", "Client"),
    )

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    actif = models.BooleanField(default=False)
    token_activation = models.CharField(max_length=100, unique=True, null=True, blank=True)
    token_activation_expire = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="client")
    date_creation = models.DateTimeField(default=timezone.now)
    suspendu = models.BooleanField(default=False)
    date_suspension = models.DateTimeField(null=True, blank=True)
    motif_suspension = models.TextField(null=True, blank=True)
    crc = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="portefeuille")
    agence = models.ForeignKey(Agence, null=True, blank=True, on_delete=models.SET_NULL, related_name="crcs")
    tentatives_echouees = models.IntegerField(default=0)
    verrouille_jusqua = models.DateTimeField(null=True, blank=True)
    token_reinitialisation = models.CharField(max_length=100, unique=True, null=True, blank=True)
    token_reinitialisation_expire = models.DateTimeField(null=True, blank=True)
    code_client = models.CharField(max_length=30, unique=True, null=True, blank=True)
    code_gestionnaire = models.CharField(max_length=30, unique=True, null=True, blank=True)
    telephone = models.CharField(max_length=30, null=True, blank=True)

    crcs_assistes = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="acrc_assistants",
        through="AcrcCrc", through_fields=("acrc", "crc"),
    )

    is_staff = models.BooleanField(default=False)

    objects = UtilisateurManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "prenom"]

    class Meta:
        db_table = "utilisateur"

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

    @property
    def is_active(self):
        return self.actif

    @is_active.setter
    def is_active(self, value):
        self.actif = value


class AcrcCrc(models.Model):
    """Table d'association ACRC <-> CRC (many-to-many) : un ACRC peut
    assister plusieurs CRC."""
    acrc = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="+")
    crc = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "acrc_crc"
        unique_together = ("acrc", "crc")


class JournalEvenement(models.Model):
    date_evenement = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(Utilisateur, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    role_acteur = models.CharField(max_length=20, null=True, blank=True)
    type_action = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "journal_evenement"
        ordering = ["-date_evenement"]


class PortefeuilleEntree(models.Model):
    """Memorise chaque ligne du dernier fichier portefeuille (Agence/CRC/
    Client) importe, pour rattacher automatiquement un client des sa
    creation."""
    code_client = models.CharField(max_length=30, unique=True)
    nom_client = models.CharField(max_length=200, null=True, blank=True)
    code_gestionnaire = models.CharField(max_length=30)
    code_agence = models.CharField(max_length=30)
    date_edition = models.CharField(max_length=20, null=True, blank=True)
    date_import = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "portefeuille_entree"


class Dossier(models.Model):
    TYPES = (("voyage", "Voyage"), ("ligne", "En ligne"))
    STATUTS = (
        ("incomplet", "Incomplet"),
        ("en_attente", "En attente"),
        ("en_cours", "En cours"),
        ("valide", "Valide"),
        ("refuse", "Refuse"),
    )

    reference = models.CharField(max_length=30, unique=True)
    type_dossier = models.CharField(max_length=20, choices=TYPES)
    periode = models.CharField(max_length=7, null=True, blank=True)
    identifiant_carte = models.CharField(max_length=10, null=True, blank=True)
    montant = models.FloatField(default=0.0)
    statut = models.CharField(max_length=20, choices=STATUTS, default="incomplet")
    date_debut_voyage = models.DateTimeField(null=True, blank=True)
    date_fin_voyage = models.DateTimeField(null=True, blank=True)
    commentaire_admin = models.TextField(null=True, blank=True)
    a_ete_mis_a_jour = models.BooleanField(default=False)
    date_creation = models.DateTimeField(default=timezone.now)
    date_mise_a_jour = models.DateTimeField(default=timezone.now)
    date_mise_en_demeure = models.DateTimeField(null=True, blank=True)
    delai_prolonge_le = models.DateTimeField(null=True, blank=True)
    complement_demande_le = models.DateTimeField(null=True, blank=True)
    client = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="dossiers")
    pris_en_charge_par = models.ForeignKey(Utilisateur, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "dossier"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.reference


class LigneTransaction(models.Model):
    date_operation = models.DateTimeField(null=True, blank=True)
    libelle = models.CharField(max_length=300)
    montant = models.FloatField()
    devise = models.CharField(max_length=10, default="XAF")
    montant_reel = models.FloatField(null=True, blank=True)
    devise_transaction = models.CharField(max_length=10, null=True, blank=True)
    hors_plafond = models.BooleanField(default=False)
    rrn = models.CharField(max_length=50, unique=True, null=True, blank=True)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name="lignes")

    class Meta:
        db_table = "ligne_transaction"

    @property
    def est_justifiee(self):
        return self.justificatifs.exists()


class Document(models.Model):
    TYPES_DOCUMENT = (
        ("passeport", "Passeport"),
        ("billet_aller", "Billet aller"),
        ("billet_retour", "Billet retour"),
        ("visa", "Visa"),
        ("autre_justificatif", "Autre justificatif"),
        ("facture_proforma", "Facture proforma"),
        ("contrat", "Contrat"),
        ("justificatif_scolarite", "Justificatif de scolarite"),
        ("justificatif_sante", "Justificatif medical / sante"),
        ("justificatif_hotel", "Reservation hotel"),
        ("justificatif", "Justificatif"),
    )
    STATUTS = (("en_attente", "En attente"), ("valide", "Valide"), ("refuse", "Refuse"))

    nom_fichier = models.CharField(max_length=200)
    type_document = models.CharField(max_length=30, choices=TYPES_DOCUMENT)
    chemin = models.CharField(max_length=300)
    donnees_ocr = models.TextField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_attente")
    motif_refus = models.TextField(null=True, blank=True)
    date_upload = models.DateTimeField(default=timezone.now)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name="documents")
    ligne = models.ForeignKey(LigneTransaction, null=True, blank=True, on_delete=models.CASCADE, related_name="justificatifs")

    class Meta:
        db_table = "document"
