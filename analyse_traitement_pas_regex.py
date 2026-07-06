import os
import cv2
import json
import re
from paddleocr import PaddleOCR

class GabonPassportParser:
    def __init__(self, lang: str = 'fr'):
        self.ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=True,
            use_textline_orientation=True,
            enable_mkldnn=False,
        )


    def extract_raw_text(self, img_data: cv2.Mat) -> str:
        result = self.ocr.predict(img_data)
        if not result:
            return ""

        extracted_lines = []
        for page in result:
            rec_texts = page.get('rec_texts', [])
            rec_scores = page.get('rec_scores', [])
            for text, score in zip(rec_texts, rec_scores):
                if score > 0.60:
                    extracted_lines.append(text.strip())

        texte_final = "\n".join(extracted_lines)
        print(f"[DEBUG OCR PASSEPORT] Texte extrait :\n{texte_final}\n---FIN---")
        return texte_final

    def parse_gabon_passport(self, ocr_text: str) -> dict:
        data = {
            "type_document": "PASSEPORT GABONAIS",
            "numero_passeport": None,
            "nom": None,
            "prenom": None,
            "nationalite": "GABONAISE",
            "date_naissance": None,
            "date_delivrance": None,
            "date_expiration": None
        }

        if not ocr_text:
            return data

        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]

        vis_nom, vis_prenom, vis_no = None, None, None
        vis_birth, vis_issue, vis_expiry = None, None, None

        for i, line in enumerate(lines):
            line_upper = line.upper()
            if ("NOM" in line_upper or "SURNAME" in line_upper) and not vis_nom:
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if not any(k in next_line.upper() for k in ["PRENOM", "GIVEN", "PASSPORT", "NATIONALITE", "REPUBLIQUE"]):
                        vis_nom = next_line.strip().upper()

            if ("PRÉNOM" in line_upper or "PRENOM" in line_upper or "GIVEN" in line_upper) and not vis_prenom:
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if not any(k in next_line.upper() for k in ["NOM", "SURNAME", "NATIONALITE", "SEXE", "DATE", "TAILLE"]):
                        vis_prenom = next_line.strip().upper()

            if not vis_no:
                pass_match = re.search(r'(\b\d{2}[A-Z]{2}\d{5}\b|\b[A-Z]{1,2}\d{7}\b)', line, re.IGNORECASE)
                if pass_match:
                    vis_no = pass_match.group(1).upper()

            if any(keyword in line_upper for keyword in ["DELIVRANCE", "DÉLIVRANCE", "ISSUE"]) and not vis_issue:
                context_text = line
                if i + 1 < len(lines):
                    context_text += " " + lines[i+1]
                date_match = re.search(r'(\d{2}[\./\s]\d{2}[\./\s]\d{2,4})', context_text)
                if date_match:
                    vis_issue = date_match.group(1).replace(" ", ".")

        all_dates = re.findall(r'(\d{2}[\./\s]\d{2}[\./\s]\d{2,4})', ocr_text)
        cleaned_dates = [d.replace(" ", ".") for d in all_dates]
        
        if len(cleaned_dates) >= 3:
            vis_birth = cleaned_dates[0]
            if not vis_issue:
                vis_issue = cleaned_dates[1]
            vis_expiry = cleaned_dates[2]
        elif len(cleaned_dates) == 2 and not vis_issue:
            vis_birth = cleaned_dates[0]
            vis_expiry = cleaned_dates[1]

        mrz_nom, mrz_prenom, mrz_no = None, None, None
        mrz_birth, mrz_expiry = None, None
        mrz1, mrz2 = None, None
        
        for line in lines:
            line_clean = line.replace(" ", "").upper()
            if "P<GAB" in line_clean:
                mrz1 = line_clean
            elif "GAB" in line_clean and line_clean != mrz1 and len(line_clean) >= 20:
                mrz2 = line_clean

        if mrz1:
            clean_mrz1 = re.sub(r'^P<GAB', '', mrz1)
            if '<<' in clean_mrz1:
                parts = clean_mrz1.split('<<')
                mrz_nom = parts[0].replace('<', ' ').strip()
                mrz_prenom = parts[1].replace('<', ' ').strip()

        if mrz2:
            idx = mrz2.find("GAB")
            if idx >= 9:
                try:
                    mrz_no = mrz2[idx-10:idx-1].replace('<', '').strip()
                    dob_raw = mrz2[idx+3:idx+9]
                    mrz_birth = f"{dob_raw[4:6]}.{dob_raw[2:4]}.{'20' if int(dob_raw[0:2]) < 50 else '19'}{dob_raw[0:2]}"
                    exp_raw = mrz2[idx+11:idx+17]
                    mrz_expiry = f"{exp_raw[4:6]}.{exp_raw[2:4]}.20{exp_raw[0:2]}"
                except Exception:
                    pass

        def reconcilier_identite(mrz_val, vis_val):
            if not mrz_val: return vis_val
            if not vis_val: return mrz_val
            norm_mrz = re.sub(r'[^A-Z]', '', mrz_val.upper())
            norm_vis = re.sub(r'[^A-Z]', '', vis_val.upper())
            if len(norm_vis) >= len(norm_mrz): return vis_val
            return mrz_val

        data["nom"] = reconcilier_identite(mrz_nom, vis_nom)
        data["prenom"] = reconcilier_identite(mrz_prenom, vis_prenom)
        data["numero_passeport"] = mrz_no if mrz_no and len(mrz_no) == 9 else (vis_no or mrz_no)
        data["date_naissance"] = mrz_birth or vis_birth
        data["date_delivrance"] = vis_issue 
        data["date_expiration"] = mrz_expiry or vis_expiry

        return data

    def process_document(self, image_path: str) -> dict:
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise FileNotFoundError(f"Impossible de lire l'image à l'emplacement : {image_path}")
            raw_text = self.extract_raw_text(img)
            if not raw_text:
                print("[DEBUG OCR PASSEPORT] raw_text est vide après extraction.")
                return {}
            return self.parse_gabon_passport(raw_text)
        except Exception as e:
            import traceback
            print(f"[DEBUG OCR PASSEPORT] EXCEPTION : {e}")
            traceback.print_exc()
            return {}