from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apurement import views_admin, views_auth, views_dossiers

urlpatterns = [
    # --- Authentification ---
    path("auth/login/", views_auth.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/moi/", views_auth.MoiView.as_view(), name="moi"),
    path("auth/activer/<str:token>/", views_auth.ActivationView.as_view(), name="activation"),
    path("auth/renvoyer-activation/", views_auth.RenvoyerActivationView.as_view(), name="renvoyer-activation"),
    path("auth/mot-de-passe-oublie/", views_auth.DemandeReinitialisationView.as_view(), name="demande-reinitialisation"),
    path("auth/reinitialiser/<str:token>/", views_auth.ConfirmerReinitialisationView.as_view(), name="confirmer-reinitialisation"),

    # --- Client ---
    path("dashboard/", views_dossiers.DashboardView.as_view(), name="dashboard"),
    path("dossier/anticiper-voyage/", views_dossiers.AnticiperVoyageView.as_view(), name="anticiper-voyage"),
    path("dossier/<int:dossier_id>/", views_dossiers.DossierDetailView.as_view(), name="dossier-detail"),
    path("dossier/<int:dossier_id>/upload/", views_dossiers.UploadDocumentView.as_view(), name="upload-document"),
    path("dossier/<int:dossier_id>/justifier/", views_dossiers.JustifierLignesView.as_view(), name="justifier-lignes"),
    path("dossier/<int:dossier_id>/annuler/", views_dossiers.AnnulerDossierView.as_view(), name="annuler-dossier"),
    path("document/<int:document_id>/", views_dossiers.VoirDocumentView.as_view(), name="voir-document"),

    # --- Admin / superviseur / CRC / ACRC ---
    path("admin/dashboard/", views_admin.AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/archive/", views_admin.AdminArchiveView.as_view(), name="admin-archive"),
    path("admin/suspendus/", views_admin.AdminSuspendusView.as_view(), name="admin-suspendus"),
    path("admin/clients/<int:utilisateur_id>/reactiver/", views_admin.AdminReactiverClientView.as_view(), name="admin-reactiver-client"),
    path("admin/dossier/<int:dossier_id>/", views_admin.AdminDossierDetailView.as_view(), name="admin-dossier-detail"),
    path("admin/dossier/<int:dossier_id>/decision/", views_admin.AdminDecisionDossierView.as_view(), name="admin-decision-dossier"),
    path("admin/dossier/<int:dossier_id>/supprimer/", views_admin.AdminSupprimerDossierView.as_view(), name="admin-supprimer-dossier"),
    path("admin/document/<int:document_id>/decision/", views_admin.AdminDocumentDecisionView.as_view(), name="admin-document-decision"),
    path("admin/import/fichier/", views_admin.AdminImportFichierView.as_view(), name="admin-import-fichier"),
    path("admin/import/portefeuille/", views_admin.AdminImportPortefeuilleView.as_view(), name="admin-import-portefeuille"),
    path("admin/utilisateurs/", views_admin.AdminUtilisateursView.as_view(), name="admin-utilisateurs"),
    path("admin/utilisateurs/<int:utilisateur_id>/basculer/", views_admin.AdminBasculerUtilisateurView.as_view(), name="admin-basculer-utilisateur"),
    path("admin/utilisateurs/<int:utilisateur_id>/supprimer/", views_admin.AdminSupprimerUtilisateurView.as_view(), name="admin-supprimer-utilisateur"),
    path("admin/journal/", views_admin.JournalView.as_view(), name="admin-journal"),
    path("admin/crcs/", views_admin.CrcArborescenceView.as_view(), name="crc-arborescence"),
    path("admin/crcs/<int:crc_id>/dossiers/", views_admin.CrcDossiersEnAttenteView.as_view(), name="crc-dossiers-en-attente"),
]
