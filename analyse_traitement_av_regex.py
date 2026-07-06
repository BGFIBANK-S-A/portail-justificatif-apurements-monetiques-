# -*- coding: utf-8 -*-
import os
import cv2
import json
import re
import traceback
from paddleocr import PaddleOCR

class FlightTicketParser:
    def __init__(self, lang='fr'):
        self.ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    def extraire_texte_brut(self, image):
        resultat = self.ocr.predict(image)
        if not resultat:
            return ""
        lignes = []
        for page in resultat:
            textes = page.get('rec_texts', [])
            scores = page.get('rec_scores', [])
            for texte, score in zip(textes, scores):
                if score > 0.55:
                    lignes.append(texte.strip())

        texte_final = "\n".join(lignes)
        print(f"[DEBUG OCR BILLET] Texte extrait :\n{texte_final}\n---FIN---")
        return texte_final

    def _nettoyer_nom_passager(self, nom_brut):
        if not nom_brut:
            return None
        nom = nom_brut.upper()
        nom = re.sub(r'\(.*?\)', '', nom)
        nom = re.sub(r'\bADULT\s*\d*\b', '', nom)
        nom = re.sub(r'\bADULTE\s*\d*\b', '', nom)
        nom = nom.replace(">", "").replace("<", "").replace(".", "").replace("»", "").strip()
        nom = nom.replace("/", " ")
        civilites = [
            r'\bMSTR\b', r'\bMRS\.?\b', r'\bMME\.?\b', r'\bMS\.?\b', r'\bMR\.?\b',
        ]
        for civ in civilites:
            nom = re.sub(civ, '', nom)
        nom = re.sub(r'(MRS|MR|MME|MS)$', '', nom).strip()
        nom = re.sub(r'\s+', ' ', nom).strip()
        return nom if len(nom) > 3 else None

    def _normaliser_date(self, date_brute):
        return date_brute.replace("/", ".").replace("-", ".").strip()

    def _est_un_nom(self, texte):
        mots = texte.split()
        if len(mots) < 2: return False
        if re.search(r'\d{3,}', texte): return False
        if '@' in texte: return False
        if len(texte) > 60: return False
        nb_lettres = sum(1 for c in texte if c.isalpha())
        if nb_lettres < len(texte) * 0.6: return False
        return True

    def _nettoyer_ville(self, ville):
        ville = re.sub(r'^[\-\+\=\~\*\.\s►→]+', '', ville).strip()
        ville = re.sub(r',.*$', '', ville).strip()
        ville = ville.rstrip('.').strip()
        return ville.title()

    def _extraire_lieux(self, lignes, compagnie):
        lieux = []
        lieux_vus = set()
        mots_exclus_lieux = [
            "ECONOMY", "BUSINESS", "CLASS", "FLIGHT", "VOL", "OK", "TERMINAL",
            "GATE", "SEAT", "CABIN", "STATUS", "STATUT", "DEPARTURE", "ARRIVAL",
            "DEPART", "ARRIVEE", "CABINE", "CONFIRMED", "CONFIRME", "OPERATED",
            "EFFECTUE", "CHECK", "BAGGAGE", "BAGAGE", "TOTAL", "BOOKING",
            "REFERENCE", "RESERVATION", "ELECTRONIC", "TICKET", "BILLET",
            "PASSENGER", "PASSAGER", "PASSENGERS", "PASSAGERS", "PREPARE",
            "POUR", "INFORMATION", "CONTACT", "SUMMARY", "TRIP", "POLICY",
            "ESSENTIAL", "ECO", "ITINERARY", "ITINERAIRE", "AIRLINE", "AIRLINES",
            "ALLIANCE", "STAR", "MEMBER", "WORLD", "FRIDAY", "SATURDAY", "SUNDAY",
            "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "LUNDI", "MARDI",
            "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE",
            "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
            "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
            "SEND", "CONFIRMATION", "EMAIL", "TIME", "SAVE", "ON",
            "VOTRE", "YOUR", "RECEIVE", "SCAN", "OBTENIR", "OBTENEZ",
            "KIOSKS", "BORNE", "GAGNEZ", "TEMPS", "IDENTIFIANT",
            "NUMERO", "CARTE", "INTERACTIVE", "CODE", "BARRES",
            "AEROPORT", "AIRPORT", "LATEST", "OPERATED", "PAR", "BY",
            "CLASSE", "ENREGISTREMENT", "FIN", "BAGAGES", "CABINE",
            "DEPARTS", "ARRIVES", "ONEWORLD", "ONWORLD",
            "ROYAL", "MAROC", "FRANCE", "ETHIOPIAN", "AIRLINES", "AIR",
            "DATE", "FROM", "VERS", "AVION", "VOLS", "MILAGE", "DUREE",
            "REPAS", "STATUT", "CONFIRME", "DISPONIBLE", "DEJEUNER",
            "ECONOMIQUE", "AEROGARE", "CONGO", "ETHIOPIA", "DEM", "REP",
        ]

        def ajouter_lieu(ville):
            ville = self._nettoyer_ville(ville)
            cle = ville.upper()
            if (len(ville) > 3 and cle not in lieux_vus and not re.search(r'\d', ville)
                and not any(m == cle or cle == m for m in mots_exclus_lieux)
                and not all(mot.upper() in mots_exclus_lieux for mot in ville.split())):
                lieux_vus.add(cle)
                lieux.append(ville)

        mois_regex_court = r'(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'

        if compagnie == "AIR FRANCE":
            for i, ligne in enumerate(lignes):
                ligne_maj = ligne.strip().upper()
                if re.match(r'^\d{1,2}' + mois_regex_court + r'\s*$', ligne_maj):
                    if i + 1 < len(lignes):
                        ville_dep = self._nettoyer_ville(lignes[i + 1].strip())
                        if len(ville_dep) > 3 and not re.search(r'\d', ville_dep):
                            ajouter_lieu(ville_dep)
                    for j in range(2, 7):
                        if i + j < len(lignes):
                            candidate = lignes[i + j].strip()
                            candidate_nettoyee = re.sub(r'^[\-\+\=\~\*\s►→]+', '', candidate).strip()
                            candidate_maj = candidate_nettoyee.upper()
                            if re.match(r'^\d{1,2}' + mois_regex_court, candidate_maj): break
                            if (len(candidate_nettoyee) > 3 and re.match(r'^[A-Za-z][A-Za-z\s\-]+$', candidate_nettoyee)
                                and not any(m in candidate_maj for m in mots_exclus_lieux) and not re.search(r'\d', candidate_nettoyee)):
                                ajouter_lieu(candidate_nettoyee)
                                break
        elif compagnie == "ROYAL AIR MAROC":
            for ligne in lignes:
                matches_fleche = re.findall(r'([A-Za-z][A-Za-z\s\-]{2,}?)\s*(?:→|->|►)\s*([A-Za-z][A-Za-z\s\-]{2,})', ligne)
                for match in matches_fleche:
                    ajouter_lieu(match[0]); ajouter_lieu(match[1])
        elif compagnie == "ETHIOPIAN AIRLINES":
            code_iata_regex = r'^[A-Z]{3}$'
            for i, ligne in enumerate(lignes):
                ligne_maj = ligne.strip().upper()
                if re.match(code_iata_regex, ligne_maj):
                    for j in range(1, 4):
                        if i + j < len(lignes):
                            candidate = lignes[i + j].strip()
                            candidate_nettoyee = self._nettoyer_ville(candidate)
                            candidate_maj = candidate_nettoyee.upper()
                            if re.match(code_iata_regex, candidate.strip().upper()): break
                            if re.search(r'\d', candidate_nettoyee): continue
                            if any(m in candidate_maj for m in mots_exclus_lieux): continue
                            if len(candidate_nettoyee) > 3:
                                ajouter_lieu(candidate_nettoyee)
                                break
                match_dest = re.search(r'DESTINATION\s+DE\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]+)+\s+DE', ligne_maj)
                if match_dest:
                    ville = re.sub(r',.*$', '', match_dest.group(1).strip().title()).strip()
                    ajouter_lieu(ville)

        return lieux

    def analyser_billet(self, texte_ocr):
        donnees = {
            "type_document": "BILLET D'AVION ELECTRONIQUE",
            "compagnie_aerienne": "INCONNUE",
            "nom_passager": None,
            "date_voyage": None,
            "toutes_les_dates_detectees": [],
            "lieux": []
        }

        if not texte_ocr: return donnees

        lignes = [l.strip() for l in texte_ocr.split('\n') if l.strip()]
        texte_majuscule = texte_ocr.upper()

        if re.search(r'\bAIR\s+FRANCE\b', texte_majuscule): donnees["compagnie_aerienne"] = "AIR FRANCE"
        elif re.search(r'\b(ROYAL AIR MAROC|RAM)\b', texte_majuscule): donnees["compagnie_aerienne"] = "ROYAL AIR MAROC"
        elif re.search(r'\bETHIOPIAN\b', texte_majuscule): donnees["compagnie_aerienne"] = "ETHIOPIAN AIRLINES"

        mots_exclus = [
            "FLIGHT", "VOL", "TICKET", "BILLET", "BOARDING", "GATE", "PORTE", "SEAT", "SIEGE", "CLASS", "CLASSE", "ZONE", "DATE", "TIME",
            "HEURE", "FROM", "DE", "TO", "VERS", "ROYAL", "MAROC", "FRANCE", "ETHIOPIAN", "AIRLINES", "AIR", "ELECTRONIC", "E-TICKET", "ETKT",
            "ITINERAIRE", "ITINERARY", "PASSAGERS", "PASSENGERS", "BOOKING", "RESERVATION", "CONFIRMED", "CONFIRMATION",
            "TRIP", "SUMMARY", "BAGGAGE", "POLICY", "ECONOMY", "ESSENTIAL", "DEPARTS", "ARRIVES", "CONTACT", "INFORMATION",
            "NOM DU PASSAGER", "PASSENGER NAME", "PREPARE POUR", "PREPARED FOR", "ENREGISTREMENT", "REQUIS", "REQUIRED", "TERMINAL", "STAR ALLIANCE",
            "CODE DE RESERVATION", "BOOKING REFERENCE", "GAGNEZ", "TEMPS", "SAVE TIME", "IDENTIFIANT", "NUMERO", "CARTE", "OBTENEZ", "KIOSKS", "BORNE",
        ]

        candidat_nom = None

        for i, ligne in enumerate(lignes):
            ligne_maj = ligne.upper()
            if "PREPARE POUR" in ligne_maj or "PREPARED FOR" in ligne_maj:
                if i + 1 < len(lignes):
                    suivante = re.sub(r'^[»>]+\s*', '', lignes[i + 1].strip().upper()).strip()
                    suivante = re.sub(r'Ethiopian.*$', '', suivante, flags=re.IGNORECASE).strip()
                    suivante = re.sub(r'[A-Z][a-z]+Airlines.*$', '', suivante).strip()
                    if self._est_un_nom(suivante) and not any(m in suivante for m in mots_exclus):
                        candidat_nom = suivante; break
            elif "NOM DU PASSAGER" in ligne_maj or "PASSENGER NAME" in ligne_maj:
                for j in range(1, 6):
                    if i + j < len(lignes):
                        suivante = lignes[i + j].strip().upper()
                        if suivante.startswith("»") or suivante.startswith(">"):
                            suivante = re.sub(r'^[»>]+\s*', '', suivante).strip()
                            if self._est_un_nom(suivante) and not any(m in suivante for m in mots_exclus):
                                candidat_nom = suivante; break
                if candidat_nom: break
            elif "PASSAGERS" in ligne_maj or "PASSENGERS" in ligne_maj:
                for j in range(1, 8):
                    if i + j < len(lignes):
                        suivante_nettoyee = re.sub(r'\bADULT\s*\d*\b|\bADULTE\s*\d*\b', '', lignes[i + j].strip().upper()).strip()
                        if any(m in suivante_nettoyee for m in mots_exclus): continue
                        if self._est_un_nom(suivante_nettoyee):
                            candidat_nom = suivante_nettoyee; break
                if candidat_nom: break
            elif re.search(r'\b(MR|MRS|MME|MS)\.?\s+[A-Z]', ligne_maj):
                if not any(m in ligne_maj for m in mots_exclus):
                    if self._est_un_nom(ligne_maj): candidat_nom = ligne_maj; break
            elif "/" in ligne_maj and not any(w in ligne_maj for w in ["VOL", "FLIGHT", "CLASS", "DATE", "BAG", "HTTP"]):
                match_slash = re.search(r'[A-Z][A-Z\- ]+\s*/\s*[A-Z][A-Z\- ]+', ligne_maj)
                if match_slash: candidat_nom = match_slash.group(0); break

        donnees["nom_passager"] = self._nettoyer_nom_passager(candidat_nom)
        donnees["lieux"] = self._extraire_lieux(lignes, donnees["compagnie_aerienne"])

        mois_regex = r'(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JANV?|FEB|FEV|MARS?|APR|AVR|JUIN|JUIL|JUN|JUL|AOU|SEP|OCT|NOV|DEC)'
        dates_numeriques = re.findall(r'(\d{2}[\./\-]\d{2}[\./\-]\d{2,4})', texte_majuscule)
        dates_textuelles = re.findall(r'\b(\d{1,2}\s*' + mois_regex + r'\.?\s*(?:\d{2,4})?)\b', texte_majuscule)

        toutes_dates = []
        dates_vues = set()

        for d in dates_numeriques:
            d_norm = self._normaliser_date(d)
            if d_norm not in dates_vues:
                dates_vues.add(d_norm); toutes_dates.append(d_norm)

        for d in dates_textuelles:
            d_propre = d.strip()
            d_cle = re.sub(r'\s+', '', d_propre)
            if not re.match(r'^\d{2}[A-Z]{3}$', d_cle) and not re.search(r'\d{4}', d_propre): continue
            if d_cle not in dates_vues and len(d_propre) >= 4:
                dates_vues.add(d_cle); toutes_dates.append(d_propre)

        donnees["toutes_les_dates_detectees"] = toutes_dates

        if dates_textuelles:
            for d in dates_textuelles:
                if re.search(r'\d{4}', d): donnees["date_voyage"] = d.strip(); break
            if not donnees["date_voyage"]: donnees["date_voyage"] = dates_textuelles[0].strip()
        elif dates_numeriques:
            donnees["date_voyage"] = self._normaliser_date(dates_numeriques[0])

        return donnees

    def traiter_document(self, chemin_image):
        try:
            image = cv2.imread(chemin_image)
            if image is None:
                raise FileNotFoundError("Image introuvable : " + chemin_image)
            texte_brut = self.extraire_texte_brut(image)
            if not texte_brut:
                print("[DEBUG OCR BILLET] texte_brut est vide après extraction.")
                return {}
            return self.analyser_billet(texte_brut)
        except Exception as e:
            print(f"[DEBUG OCR BILLET] EXCEPTION : {e}")
            traceback.print_exc()
            return {}