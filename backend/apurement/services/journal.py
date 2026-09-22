"""Journalisation des actions cles (connexions, decisions, gestion des
comptes, imports...), consultable par les administrateurs/superviseurs."""


def journaliser(type_action, description=None, utilisateur=None):
    from apurement.models import JournalEvenement

    JournalEvenement.objects.create(
        type_action=type_action,
        description=description,
        utilisateur=utilisateur,
        role_acteur=getattr(utilisateur, "role", None),
    )
