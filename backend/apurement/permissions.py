from rest_framework.permissions import BasePermission

ROLES_PERSONNEL_BANQUE = ("admin", "superviseur", "crc", "acrc")


class EstAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class EstSuperviseurOuAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("admin", "superviseur"))


class EstPersonnelBanque(BasePermission):
    """Admin, superviseur, CRC ou ACRC : tout role autre que client."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ROLES_PERSONNEL_BANQUE)


def autorise_dossier(utilisateur, dossier):
    """Un membre du personnel (hors client) peut consulter un dossier si :
    - il est admin ou superviseur (acces global) ;
    - il est le CRC du client titulaire du dossier ;
    - il est un ACRC assistant ce CRC."""
    if utilisateur.role in ("admin", "superviseur"):
        return True
    client = dossier.client
    if utilisateur.role == "crc":
        return client.crc_id == utilisateur.id
    if utilisateur.role == "acrc":
        return client.crc_id and utilisateur.crcs_assistes.filter(id=client.crc_id).exists()
    return False


def filtrer_dossiers_actionnables(queryset, utilisateur=None):
    """Ecarte les dossiers dont le statut ne necessite plus d'action visible
    (valide/refuse) — utilise pour les listes 'en attente'."""
    return queryset.exclude(statut__in=("valide", "refuse"))
