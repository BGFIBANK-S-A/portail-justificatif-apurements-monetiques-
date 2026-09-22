"""Import du fichier journalier de transactions monetique et du fichier
portefeuille (Agence/CRC/Client). Portage fidele de la logique Flask
(app.py : _importer_fichier, _importer_portefeuille, _classifier_flux,
_identifiant_carte...). Conserve a l'identique les regles de seuil, de
regroupement par carte/voyage et de deduplication RRN, durement etablies
face au texte reglementaire (LC BEAC 004/GR/2022)."""
import re
import secrets
import unicodedata
import uuid
from datetime import datetime, timedelta

import pandas as pd
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone as django_timezone

from apurement.models import (
    Agence,
    Dossier,
    LigneTransaction,
    PortefeuilleEntree,
    Utilisateur,
)
from apurement.services.notifications import envoyer_email
from apurement.services.journal import journaliser

ACTIVATION_DUREE_VALIDITE_JOURS = settings.ACTIVATION_DUREE_VALIDITE_JOURS

COL_EMAIL, COL_NOM, COL_DATE, COL_MONTANT, COL_MARCHAND, COL_PAYS = (
    "EM_PAYCO_EMAIL", "NOM_SUR_CARTE", "DATE_TRANSACTION", "CONTRE_VALEUR_XAF", "MARCHAND", "PAYS",
)
COL_MONTANT_REEL, COL_DEVISE_TRANSACTION = "MONTANT_TRX", "DEVISE_TRANSACTION"
COL_CODE_CLIENT = "CODE_CLIENT"
COL_TC_CODE, COL_MOTO, COL_RRN = "TC_CODE", "MOTO", "RRN"
COL_REPONSE, COL_LIBELLE_TYPE, COL_TELEPHONE = "REPONSE", "LIBELLE", "EM_PAYCO_PHONE"
COL_NUMERO_CARTE = "NUMERO_DE_CARTE"
COLS_REQUISES = (COL_EMAIL, COL_NOM, COL_DATE, COL_MONTANT, COL_TC_CODE, COL_MOTO, COL_RRN)

COL_CODE_AGENCE, COL_NOM_AGENCE = "code_agence", "nom_agence"
COL_CODE_GESTIONNAIRE, COL_NOM_GESTIONNAIRE = "code_gestionnaire", "nom_gestionnaire"
COL_CODE_CLIENT_PORTEFEUILLE, COL_NOM_CLIENT_PORTEFEUILLE = "code_client", "nom_client"
COLS_REQUISES_PORTEFEUILLE = (COL_CODE_AGENCE, COL_CODE_GESTIONNAIRE, COL_CODE_CLIENT_PORTEFEUILLE)


def _sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def _identifiant_carte(numero_carte):
    """Derive un identifiant de carte sans conserver le PAN complet : les 4
    derniers caracteres non vides suffisent a distinguer les cartes d'un meme
    client (le seuil reglementaire s'applique par carte, pas par client)."""
    if numero_carte is None or (isinstance(numero_carte, float) and pd.isna(numero_carte)):
        return None
    chiffres = re.sub(r"\D", "", str(numero_carte))
    return chiffres[-4:] if chiffres else None


def _classifier_flux(tc_code, moto):
    """Determine le flux (voyage/en ligne) d'une transaction, a partir de
    TC_CODE et MOTO :
      - TPE/retrait (voyage) : TC_CODE 7000 ou 5000, MOTO = NON MOTO
      - Paiement en ligne     : TC_CODE 5000, MOTO = MOTO
    Renvoie None si la combinaison n'est pas reconnue."""
    try:
        code = int(float(str(tc_code).strip()))
    except (TypeError, ValueError):
        return None
    moto_norm = _sans_accents(str(moto or "")).strip().upper()
    if moto_norm == "MOTO" and code == 5000:
        return "ligne"
    if moto_norm == "NON MOTO" and code in (7000, 5000):
        return "voyage"
    return None


def _separer_nom(nom_complet):
    parts = str(nom_complet).split()
    return (parts[0], " ".join(parts[1:])) if len(parts) >= 2 else (parts[0] if parts else "CLIENT", "")


def _normaliser_code_client(valeur):
    """Normalise un CODE_CLIENT en chaine de 7 chiffres, quelle que soit sa
    forme d'origine (entier, flottant Excel type 1101168.0, ou texte)."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return None
    texte = str(valeur).strip()
    if texte == "" or texte.lower() == "nan":
        return None
    try:
        return str(int(float(texte))).zfill(7)
    except (TypeError, ValueError):
        return texte


def _normaliser_code(valeur):
    """Normalise un code agence/gestionnaire lu depuis Excel : retire le '.0'
    parasite sans toucher aux zeros non significatifs."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ""
    texte = str(valeur).strip()
    if texte.endswith(".0") and texte[:-2].isdigit():
        texte = texte[:-2]
    return texte


def _lire_avec_entete(chemin):
    for h in (0, 1, 2, 3):
        try:
            df = pd.read_excel(chemin, header=h)
            df.columns = df.columns.astype(str).str.strip().str.upper()
            if all(col in df.columns for col in COLS_REQUISES):
                return df
        except Exception:
            continue
    df = pd.read_csv(chemin) if str(chemin).endswith(".csv") else pd.read_excel(chemin)
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df


@db_transaction.atomic
def importer_fichier(chemin, base_url=None):
    """Importe le fichier journalier de transactions monetique. Le flux
    (voyage ou en ligne) est determine ligne par ligne via TC_CODE + MOTO. Les
    transactions deja importees (meme RRN) sont ignorees, ce qui permet de
    retransmettre un fichier journalier sans creer de doublons."""
    base_url = base_url or settings.FRONTEND_URL
    df = _lire_avec_entete(chemin)

    manquantes = [c for c in COLS_REQUISES if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes introuvables : {', '.join(manquantes)}")

    nb_lues = len(df)

    df[COL_EMAIL] = df[COL_EMAIL].astype(str).str.strip().str.lower()
    df = df[df[COL_EMAIL].str.contains("@", na=False)].copy()
    nb_email_invalide = nb_lues - len(df)

    nb_reponse_echouee = 0
    if COL_REPONSE in df.columns:
        avant = len(df)
        reponse_normalisee = df[COL_REPONSE].astype(str).apply(_sans_accents).str.upper()
        df = df[reponse_normalisee.str.contains("SUCCES", na=False)].copy()
        nb_reponse_echouee = avant - len(df)

    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    df[COL_DATE] = df[COL_DATE].apply(lambda x: x.replace(tzinfo=None) if pd.notna(x) else x)
    df[COL_MONTANT] = pd.to_numeric(
        df[COL_MONTANT].astype(str).str.replace(r"[\s ]", "", regex=True).str.replace(",", "", regex=False),
        errors="coerce",
    )
    if COL_MONTANT_REEL in df.columns:
        df[COL_MONTANT_REEL] = pd.to_numeric(df[COL_MONTANT_REEL], errors="coerce")

    avant = len(df)
    df = df[df[COL_DATE].notna() & df[COL_MONTANT].notna()].copy()
    nb_date_ou_montant_illisible = avant - len(df)

    df["FLUX"] = df.apply(lambda r: _classifier_flux(r.get(COL_TC_CODE), r.get(COL_MOTO)), axis=1)
    nb_ignorees_flux = int(df["FLUX"].isna().sum())
    df = df[df["FLUX"].notna()].copy()

    nb_doublons_rrn = 0
    if COL_RRN in df.columns:
        df[COL_RRN] = df[COL_RRN].astype(str).str.strip()
        avant = len(df)
        df = df.drop_duplicates(subset=[COL_RRN], keep="first")
        nb_doublons_rrn += avant - len(df)
        rrn_existants = set(
            LigneTransaction.objects.exclude(rrn__isnull=True).values_list("rrn", flat=True)
        )
        avant = len(df)
        df = df[~df[COL_RRN].isin(rrn_existants)].copy()
        nb_doublons_rrn += avant - len(df)

    df["CARTE_ID"] = df[COL_NUMERO_CARTE].apply(_identifiant_carte) if COL_NUMERO_CARTE in df.columns else None

    df = df.sort_values(by=[COL_EMAIL, "FLUX", COL_DATE])

    resume = {
        "comptes_crees": 0, "comptes_existants": 0, "dossiers_crees": 0, "dossiers_actualises": 0,
        "dossiers_ignores": 0, "lignes": 0, "clients_rattaches_auto": 0, "a_notifier": [],
        "lignes_lues": nb_lues, "lignes_email_invalide": nb_email_invalide,
        "lignes_reponse_echouee": nb_reponse_echouee, "lignes_date_ou_montant_illisible": nb_date_ou_montant_illisible,
        "lignes_ignorees_flux": nb_ignorees_flux, "lignes_doublons": nb_doublons_rrn,
    }

    # Deux seuils distincts, conformement a la reglementation :
    # - TPE/retrait (voyage) : la preuve de voyage (passeport/billet) est
    #   demandee des la 1ere transaction hors CEMAC, mais seule la part du
    #   cumul qui depasse 5 000 000 FCFA doit etre justifiee transaction par
    #   transaction.
    # - Paiement en ligne : un seul et meme seuil cumule de 1 000 000 FCFA
    #   pour la notification comme pour la justification.
    SEUILS = {"voyage": settings.SEUIL_VOYAGE_XAF, "ligne": settings.SEUIL_LIGNE_XAF}
    a_notifier_par_email = {}

    for (email, flux, carte_id), groupe in df.groupby([COL_EMAIL, "FLUX", "CARTE_ID"], dropna=False):
        min_date_apercu = groupe[COL_DATE].min().to_pydatetime()
        utilisateur_existant = Utilisateur.objects.filter(email=email).first()

        dossier = None
        baseline = 0.0
        if utilisateur_existant:
            if flux == "voyage":
                # Un dossier voyage regroupe les transactions d'UN MEME voyage
                # SUR UNE MEME CARTE. Tant que les dates du voyage ne sont pas
                # connues (renseignees seulement a l'upload du billet), on se
                # base sur les dates des transactions deja rattachees a ce
                # dossier.
                candidats = Dossier.objects.filter(
                    client=utilisateur_existant, type_dossier="voyage", identifiant_carte=carte_id,
                    statut__in=("incomplet", "en_attente", "en_cours"),
                )
                for cand in candidats:
                    if cand.date_debut_voyage and cand.date_fin_voyage:
                        bornes = (cand.date_debut_voyage.replace(tzinfo=None), cand.date_fin_voyage.replace(tzinfo=None))
                    else:
                        dates_lignes = [l.date_operation.replace(tzinfo=None) for l in cand.lignes.all() if l.date_operation]
                        bornes = (min(dates_lignes), max(dates_lignes)) if dates_lignes else None
                    if bornes is None:
                        dossier = cand
                        break
                    if (bornes[0] - timedelta(days=15)) <= min_date_apercu <= (bornes[1] + timedelta(days=15)):
                        dossier = cand
                        break
            else:
                dossier = Dossier.objects.filter(
                    client=utilisateur_existant, type_dossier="ligne",
                    periode=min_date_apercu.strftime("%Y-%m"), identifiant_carte=carte_id,
                ).first()
            if dossier:
                baseline = sum(l.montant for l in dossier.lignes.all())

        groupe = groupe.assign(CUMUL_CALCULE=baseline + groupe[COL_MONTANT].cumsum())
        lignes_depassement = groupe[groupe["CUMUL_CALCULE"] > SEUILS[flux]]

        nom_complet = str(groupe.iloc[0][COL_NOM]).strip()
        nom, prenom = _separer_nom(nom_complet)
        code_client = _normaliser_code_client(groupe.iloc[0].get(COL_CODE_CLIENT)) if COL_CODE_CLIENT in df.columns else None
        telephone = _normaliser_code(groupe.iloc[0].get(COL_TELEPHONE)) if COL_TELEPHONE in df.columns else ""
        telephone = telephone or None

        utilisateur = utilisateur_existant
        if not utilisateur:
            expiration_activation = django_timezone.now() + timedelta(days=ACTIVATION_DUREE_VALIDITE_JOURS)
            utilisateur = Utilisateur.objects.create(
                nom=nom, prenom=prenom, email=email, telephone=telephone,
                token_activation=secrets.token_urlsafe(24), token_activation_expire=expiration_activation,
            )
            resume["comptes_crees"] += 1
        else:
            resume["comptes_existants"] += 1
            if telephone and utilisateur.telephone != telephone:
                utilisateur.telephone = telephone

        if code_client and utilisateur.code_client != code_client and not Utilisateur.objects.filter(
            code_client=code_client
        ).exclude(id=utilisateur.id).exists():
            utilisateur.code_client = code_client

        if not utilisateur.crc_id and utilisateur.code_client:
            entree = PortefeuilleEntree.objects.filter(code_client=utilisateur.code_client).first()
            if entree:
                crc_auto = Utilisateur.objects.filter(code_gestionnaire=entree.code_gestionnaire, role="crc").first()
                if crc_auto:
                    utilisateur.crc_id = crc_auto.id
                    resume["clients_rattaches_auto"] = resume.get("clients_rattaches_auto", 0) + 1
        utilisateur.save()

        min_date = min_date_apercu
        dossier_nouveau = dossier is None

        if not dossier:
            if flux == "voyage":
                ref = f"DOC-{min_date.year}-VY{uuid.uuid4().hex[:5].upper()}"
                dossier = Dossier.objects.create(
                    reference=ref, type_dossier="voyage", periode=min_date.strftime("%Y-%m"),
                    montant=0.0, statut="incomplet", client=utilisateur, identifiant_carte=carte_id,
                )
            else:
                periode_ligne = min_date.strftime("%Y-%m")
                ref = f"DOC-{periode_ligne[:4]}-LN{uuid.uuid4().hex[:5].upper()}"
                dossier = Dossier.objects.create(
                    reference=ref, type_dossier="ligne", periode=periode_ligne,
                    montant=0.0, statut="incomplet", client=utilisateur, identifiant_carte=carte_id,
                )
            resume["dossiers_crees"] += 1
        else:
            if dossier.statut in ("valide", "refuse"):
                dossier.statut = "incomplet"
            resume["dossiers_actualises"] += 1
            dossier.save()

        existing_lines = {
            (l.date_operation.strftime("%Y-%m-%d") if l.date_operation else "", l.libelle, l.montant)
            for l in dossier.lignes.all()
        }
        nouvelles_lignes = 0
        nouvelles_lignes_en_depassement = 0
        index_depassement = set(lignes_depassement.index)

        nouvelles_lignes_objets = []
        for idx, row in groupe.iterrows():
            m, p = str(row.get(COL_MARCHAND, "")).strip(), str(row.get(COL_PAYS, "")).strip()
            lib_type = str(row.get(COL_LIBELLE_TYPE, "")).strip()
            lib = m if m and m.lower() != "nan" else "Transaction"
            if lib_type and lib_type.lower() != "nan" and lib_type.upper() != lib.upper():
                lib = f"{lib} ({lib_type})"
            if p and p.lower() != "nan":
                lib = f"{lib} - {p}"
            date_op = row[COL_DATE].to_pydatetime() if pd.notna(row[COL_DATE]) else None
            mnt = float(row[COL_MONTANT]) if pd.notna(row[COL_MONTANT]) else 0.0
            mnt_reel = row.get(COL_MONTANT_REEL)
            mnt_reel = float(mnt_reel) if mnt_reel is not None and pd.notna(mnt_reel) else None
            devise_op = str(row.get(COL_DEVISE_TRANSACTION, "")).strip().upper() or None
            if devise_op == "NAN":
                devise_op = None
            rrn = str(row.get(COL_RRN, "")).strip() or None
            en_depassement = idx in index_depassement

            key = (date_op.strftime("%Y-%m-%d") if date_op else "", lib, mnt)
            if key not in existing_lines:
                nouvelles_lignes_objets.append(LigneTransaction(
                    date_operation=date_op, libelle=lib[:300], montant=mnt, dossier=dossier,
                    montant_reel=mnt_reel, devise_transaction=devise_op, hors_plafond=not en_depassement, rrn=rrn,
                ))
                existing_lines.add(key)
                nouvelles_lignes += 1
                resume["lignes"] += 1
                if en_depassement:
                    dossier.montant += mnt
                    nouvelles_lignes_en_depassement += 1

        if nouvelles_lignes_objets:
            LigneTransaction.objects.bulk_create(nouvelles_lignes_objets)
        dossier.save()

        declenche_notification = (flux == "voyage" and dossier_nouveau) or nouvelles_lignes_en_depassement > 0
        if nouvelles_lignes > 0 and declenche_notification:
            entree_notif = a_notifier_par_email.setdefault(email, {
                "email": email, "nom": nom_complet, "actif": utilisateur.actif, "nb": 0,
                "references": [], "lien": None, "_utilisateur": utilisateur,
            })
            entree_notif["nb"] += nouvelles_lignes
            entree_notif["references"].append(dossier.reference)

    for entree in a_notifier_par_email.values():
        utilisateur = entree.pop("_utilisateur")
        lien = f"{base_url}/activer/{utilisateur.token_activation}" if not utilisateur.actif else f"{base_url}/login"
        entree["lien"] = lien
        if not utilisateur.actif:
            corps = (
                f"Bonjour {utilisateur.prenom},\n\n"
                "Une operation necessitant une justification a ete enregistree sur votre compte. "
                "Definissez votre mot de passe pour acceder au Portail Justificatif d'Apurement "
                f"(lien valable {ACTIVATION_DUREE_VALIDITE_JOURS} jours) :\n{lien}\n\n"
                "Cordialement,\nBGFIBank Gabon"
            )
            try:
                envoyer_email(utilisateur.email, "Justificatif requis - Acces au Portail Justificatif d'Apurement", corps)
            except Exception as e:
                journaliser("erreur_notification", f"Echec de l'envoi du lien d'acces a {utilisateur.email} : {e}")
        resume["a_notifier"].append(entree)

    return resume


@db_transaction.atomic
def importer_portefeuille(chemin, progress_cb=None):
    """Importe le referentiel Agence / Gestionnaire (CRC) / Client et relie
    chaque client existant (identifie par CODE_CLIENT) a son CRC. Cree
    l'agence et le compte CRC s'ils sont absents ; le compte CRC est cree
    avec un email provisoire (a completer par un administrateur).
    progress_cb(traite, total), si fourni, est appele apres chaque ligne."""
    df = pd.read_csv(chemin) if str(chemin).endswith(".csv") else pd.read_excel(chemin)
    df.columns = [str(c).strip() for c in df.columns]

    manquantes = [c for c in COLS_REQUISES_PORTEFEUILLE if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes introuvables : {', '.join(manquantes)}")

    resume = {"agences_creees": 0, "crc_crees": 0, "clients_relies": 0, "clients_introuvables": [], "crc_a_completer": []}
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        code_agence = _normaliser_code(row.get(COL_CODE_AGENCE))
        code_gestionnaire = _normaliser_code(row.get(COL_CODE_GESTIONNAIRE))
        code_client = _normaliser_code_client(row.get(COL_CODE_CLIENT_PORTEFEUILLE))
        if not code_agence or not code_gestionnaire or not code_client:
            if progress_cb:
                progress_cb(i, total)
            continue

        nom_agence = str(row.get(COL_NOM_AGENCE, "")).strip() or code_agence
        nom_gestionnaire = str(row.get(COL_NOM_GESTIONNAIRE, "")).strip() or code_gestionnaire
        nom_client = str(row.get(COL_NOM_CLIENT_PORTEFEUILLE, "")).strip()

        agence = Agence.objects.filter(code_agence=code_agence).first()
        if not agence:
            # Le nom d'agence n'est pas toujours discriminant (ex : plusieurs
            # codes agence partagent le meme intitule generique dans le
            # fichier portefeuille, "Agence Centrale" par exemple) : on
            # reutilise l'agence existante de ce nom plutot que d'echouer sur
            # la contrainte d'unicite de Agence.nom.
            agence = Agence.objects.filter(nom=nom_agence).first()
            if agence:
                if not agence.code_agence:
                    agence.code_agence = code_agence
                    agence.save()
            else:
                agence = Agence.objects.create(nom=nom_agence, code_agence=code_agence)
                resume["agences_creees"] += 1

        crc = Utilisateur.objects.filter(code_gestionnaire=code_gestionnaire, role="crc").first()
        if not crc:
            nom_p, prenom_p = _separer_nom(nom_gestionnaire)
            email_provisoire = f"crc-{re.sub(r'[^a-z0-9]', '', code_gestionnaire.lower())}@a-completer.bgfi.ga"
            crc = Utilisateur.objects.create(
                nom=nom_p, prenom=prenom_p, email=email_provisoire, role="crc",
                actif=False, agence=agence, code_gestionnaire=code_gestionnaire,
            )
            resume["crc_crees"] += 1
            resume["crc_a_completer"].append({
                "nom": f"{prenom_p} {nom_p}", "code_gestionnaire": code_gestionnaire, "email_provisoire": email_provisoire,
            })
        elif crc.agence_id != agence.id:
            crc.agence = agence
            crc.save()

        date_edition = str(row.get("date_edition", "")).strip()
        entree = PortefeuilleEntree.objects.filter(code_client=code_client).first()
        if not entree:
            entree = PortefeuilleEntree(code_client=code_client)
        entree.nom_client, entree.code_gestionnaire, entree.code_agence = nom_client, code_gestionnaire, code_agence
        entree.date_edition = date_edition
        entree.date_import = django_timezone.now()
        entree.save()

        client = Utilisateur.objects.filter(code_client=code_client, role="client").first()
        if client:
            client.crc = crc
            client.save()
            resume["clients_relies"] += 1
        else:
            resume["clients_introuvables"].append({"code_client": code_client, "nom_client": nom_client})

        if progress_cb:
            progress_cb(i, total)

    return resume
