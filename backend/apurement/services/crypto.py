"""Chiffrement au repos des documents uploades (passeports, billets,
justificatifs). DOCUMENTS_ENCRYPTION_KEY doit venir de l'environnement en
production (sinon une cle temporaire est generee : fichiers dechiffrables
uniquement pendant la duree de vie du process, a eviter en production)."""
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_cle = settings.DOCUMENTS_ENCRYPTION_KEY
if not _cle:
    _cle = Fernet.generate_key().decode()
    print(f"ATTENTION : DOCUMENTS_ENCRYPTION_KEY non definie, cle temporaire generee : {_cle}")
_fernet = Fernet(_cle.encode())


def sauvegarder_fichier_chiffre(fichier_django, chemin_destination):
    os.makedirs(os.path.dirname(chemin_destination), exist_ok=True)
    contenu = fichier_django.read()
    with open(chemin_destination, "wb") as f:
        f.write(_fernet.encrypt(contenu))


def lire_fichier_dechiffre(chemin):
    with open(chemin, "rb") as f:
        contenu = f.read()
    try:
        return _fernet.decrypt(contenu)
    except InvalidToken:
        return contenu


def extension_valide(nom_fichier):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in settings.EXTENSIONS_AUTORISEES


def est_image(nom_fichier):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg"}
