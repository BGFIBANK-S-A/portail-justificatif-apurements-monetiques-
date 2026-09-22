"""Cycle de vie du dossier : statut, delais reglementaires (LC BEAC
004/GR/2022), detection d'incoherences OCR. Portage fidele de la logique
metier Flask (app.py) — cf. commentaires en francais conserves a l'identique
pour la tracabilite avec le cahier des charges."""
import json
import re
import unicodedata
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

DELAI_JUSTIFICATION_JOURS = settings.DELAI_JUSTIFICATION_JOURS
DELAI_MISE_EN_DEMEURE_JOURS = settings.DELAI_MISE_EN_DEMEURE_JOURS


def _docs_dossier(dossier):
    return {d.type_document: d for d in dossier.documents.filter(ligne__isnull=True)}


def montant_justifie(dossier):
    """Somme des lignes actuellement justifiees (document fourni et non
    refuse). Le client choisit librement lesquelles justifier."""
    total = 0.0
    for l in dossier.lignes.all():
        justifs = list(l.justificatifs.all())
        if justifs and not any(j.statut == "refuse" for j in justifs):
            total += l.montant
    return total


def preuve_voyage_manquante(dossier, par_type=None):
    """Un dossier voyage exige la preuve de voyage (passeport + billet) des la
    1ere transaction hors CEMAC, independamment du montant (LC BEAC
    004/GR/2022 §2.1/§3)."""
    if dossier.type_dossier != "voyage":
        return False
    if par_type is None:
        par_type = _docs_dossier(dossier)
    passeport_ok = "passeport" in par_type and par_type["passeport"].statut != "refuse"
    billet_ok = (
        ("billet_aller" in par_type and par_type["billet_aller"].statut != "refuse")
        or ("billet_retour" in par_type and par_type["billet_retour"].statut != "refuse")
    )
    return not (passeport_ok and billet_ok)


def recalculer_statut(dossier):
    if dossier.statut in ("valide", "refuse"):
        return
    par_type = _docs_dossier(dossier)

    lignes_ok = True
    if dossier.lignes.exists():
        lignes_ok = montant_justifie(dossier) >= dossier.montant - 0.01

    if dossier.type_dossier == "voyage":
        dossier.statut = "incomplet" if (preuve_voyage_manquante(dossier, par_type) or not lignes_ok) else "en_attente"
    else:
        dossier.statut = "en_attente" if (lignes_ok and dossier.lignes.exists()) else "incomplet"


def _naif(dt):
    return dt.replace(tzinfo=None) if dt and timezone.is_aware(dt) else dt


def _date_reference_delai(dossier):
    """Date de depart du delai reglementaire : date de la 1ere operation du
    dossier, ou date de la derniere prolongation si plus recente."""
    dates = [_naif(l.date_operation) for l in dossier.lignes.all() if l.date_operation]
    ref = min(dates) if dates else _naif(dossier.date_creation)
    prolongation = _naif(dossier.delai_prolonge_le)
    if prolongation and ref and prolongation > ref:
        return prolongation
    return ref


def jours_restants_justification(dossier):
    if dossier.statut in ("valide", "refuse"):
        return None
    ref = _date_reference_delai(dossier)
    if not ref:
        return None
    echeance = ref + timedelta(days=DELAI_JUSTIFICATION_JOURS)
    return (echeance - _naif(datetime.now())).days


def verifier_delais_dossiers():
    """A executer periodiquement (celery beat / cron) : applique les
    echeances reglementaires (mise en demeure a J+30, suspension a J+38)."""
    from apurement.models import Dossier  # import tardif pour eviter les cycles

    maintenant = _naif(datetime.now())
    resume = {"mises_en_demeure": [], "suspensions": []}

    for dossier in Dossier.objects.exclude(statut__in=("valide", "refuse")):
        ref = _date_reference_delai(dossier)
        if not ref:
            continue

        if not dossier.date_mise_en_demeure:
            echeance_justification = ref + timedelta(days=DELAI_JUSTIFICATION_JOURS)
            if maintenant >= echeance_justification:
                dossier.date_mise_en_demeure = echeance_justification
                dossier.commentaire_admin = (
                    "Mise en demeure automatique (delai de justification de 30 jours depasse). "
                    f"Documents attendus sous {DELAI_MISE_EN_DEMEURE_JOURS} jours, faute de quoi vos "
                    "instruments de paiement seront suspendus, conformement a la Lettre Circulaire "
                    "BEAC n 004/GR/2022."
                )
                dossier.save()
                resume["mises_en_demeure"].append(dossier.reference)
                continue

        if dossier.date_mise_en_demeure:
            echeance_suspension = dossier.date_mise_en_demeure + timedelta(days=DELAI_MISE_EN_DEMEURE_JOURS)
            if maintenant >= echeance_suspension and not dossier.client.suspendu:
                client = dossier.client
                client.suspendu = True
                client.date_suspension = timezone.now()
                client.motif_suspension = (
                    f"Suspension automatique : justificatifs non transmis pour le dossier {dossier.reference} "
                    f"dans le delai de {DELAI_MISE_EN_DEMEURE_JOURS} jours suivant la mise en demeure."
                )
                client.save()
                resume["suspensions"].append(client.email)

    return resume


# ---------------------------------------------------------------------------
# Detection d'incoherences (controle assiste des dossiers) — purement
# indicatif : ne bloque jamais une action, ne fait que la mettre en evidence.
# ---------------------------------------------------------------------------

def _sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def _normaliser_texte_identite(valeur):
    return _sans_accents(str(valeur or "")).upper().replace("-", " ").strip()


def _identite_correspond(nom_extrait, client):
    if not nom_extrait:
        return True
    tokens_client = set(_normaliser_texte_identite(client.nom).split())
    tokens_extrait = set(_normaliser_texte_identite(nom_extrait).split())
    if not tokens_client or not tokens_extrait:
        return True
    return bool(tokens_client & tokens_extrait)


def _parser_date_simple(valeur):
    if not valeur:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(valeur).strip(), fmt)
        except ValueError:
            continue
    return None


MOIS_MAP = {
    "JAN": 1, "JANV": 1, "JANUARY": 1, "FEB": 2, "FEV": 2, "FEBRUARY": 2,
    "MAR": 3, "MARS": 3, "MARCH": 3, "APR": 4, "AVR": 4, "APRIL": 4,
    "MAY": 5, "MAI": 5, "JUN": 6, "JUIN": 6, "JUNE": 6,
    "JUL": 7, "JUIL": 7, "JULY": 7, "AUG": 8, "AOU": 8, "AUGUST": 8,
    "SEP": 9, "SEPTEMBER": 9, "OCT": 10, "OCTOBER": 10,
    "NOV": 11, "NOVEMBER": 11, "DEC": 12, "DECEMBER": 12,
}


def extraire_dates_ocr(resultat_ocr):
    dates = []
    if not isinstance(resultat_ocr, dict):
        return dates
    valeurs_brutes = []
    if resultat_ocr.get("toutes_les_dates_detectees"):
        valeurs_brutes.extend(resultat_ocr.get("toutes_les_dates_detectees"))
    elif resultat_ocr.get("date_voyage"):
        valeurs_brutes.append(resultat_ocr.get("date_voyage"))

    for val in valeurs_brutes:
        val_str = str(val).strip().upper()
        date_parse = _parser_date_simple(val_str)
        if not date_parse:
            match = re.search(r"(\d{1,2})\s*([A-Z]{3,10})\s*(\d{2,4})?", val_str)
            if match:
                jour = int(match.group(1))
                mois_str, annee_str = match.group(2), match.group(3)
                mois = next((num for cle, num in MOIS_MAP.items() if cle in mois_str), None)
                if mois:
                    annee = int(annee_str) if annee_str else datetime.now().year
                    if annee < 100:
                        annee += 2000
                    try:
                        date_parse = datetime(annee, mois, jour)
                    except ValueError:
                        pass
        if date_parse:
            dates.append(date_parse)
    return dates


def detecter_incoherences(dossier):
    """Compare les donnees extraites par OCR (identite passeport/billet,
    dates) a l'identite du client et aux dates declarees."""
    incoherences = []
    if dossier.type_dossier != "voyage":
        return incoherences

    par_type = _docs_dossier(dossier)
    ocr = {t: json.loads(d.donnees_ocr) for t, d in par_type.items() if d.donnees_ocr}

    passeport = ocr.get("passeport")
    client = dossier.client
    if passeport:
        nom_complet_passeport = f"{passeport.get('nom') or ''} {passeport.get('prenom') or ''}".strip()
        if nom_complet_passeport and not _identite_correspond(nom_complet_passeport, client):
            incoherences.append(
                f"Le nom sur le passeport ({nom_complet_passeport}) ne correspond pas au client ({client.prenom} {client.nom})."
            )
        expiration = _parser_date_simple(passeport.get("date_expiration"))
        if expiration and dossier.date_debut_voyage and expiration < _naif(dossier.date_debut_voyage):
            incoherences.append(f"Le passeport est expire depuis le {expiration.strftime('%d/%m/%Y')}, avant la date de depart declaree.")

    dates_billets = {}
    for type_billet in ("billet_aller", "billet_retour"):
        billet = ocr.get(type_billet)
        if not billet:
            continue
        nom_passager = billet.get("nom_passager")
        if nom_passager and not _identite_correspond(nom_passager, client):
            incoherences.append(
                f"Le nom du passager sur le {type_billet.replace('_', ' ')} ({nom_passager}) ne correspond pas au client ({client.prenom} {client.nom})."
            )
        dates_detectees = extraire_dates_ocr(billet)
        if dates_detectees:
            dates_billets[type_billet] = dates_detectees[0]

    if "billet_aller" in dates_billets and "billet_retour" in dates_billets:
        if dates_billets["billet_aller"] > dates_billets["billet_retour"]:
            incoherences.append("La date du billet retour est anterieure a celle du billet aller.")

    if dossier.date_debut_voyage and dossier.date_fin_voyage:
        bornes = (("billet_aller", _naif(dossier.date_debut_voyage)), ("billet_retour", _naif(dossier.date_fin_voyage)))
        for type_billet, reference in bornes:
            if type_billet in dates_billets and abs((dates_billets[type_billet] - reference).days) > 2:
                incoherences.append(
                    f"La date du {type_billet.replace('_', ' ')} ({dates_billets[type_billet].strftime('%d/%m/%Y')}) s'ecarte de la periode de voyage declaree."
                )

    return incoherences
