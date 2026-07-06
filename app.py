# -*- coding: utf-8 -*-
from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_file, flash, jsonify)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import re
import uuid
import json
import secrets
import shutil
import unicodedata
import threading

import pandas as pd

app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

app.config['SECRET_KEY'] = 'bgfi_portail_secret_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portail.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['BASE_URL'] = 'http://127.0.0.1:5000'

EXTENSIONS_AUTORISEES = {'png', 'jpg', 'jpeg', 'pdf'}

def extension_valide(nom_fichier):
    return '.' in nom_fichier and nom_fichier.rsplit('.', 1)[1].lower() in EXTENSIONS_AUTORISEES

def est_image(nom_fichier):
    return '.' in nom_fichier and nom_fichier.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def chemin_dossier_upload(utilisateur_id, reference):
    chemin = os.path.join(app.config['UPLOAD_FOLDER'], f'client_{utilisateur_id}', reference)
    os.makedirs(chemin, exist_ok=True)
    return chemin

db = SQLAlchemy(app)

# =========================================================
# MOTEURS OCR
# =========================================================

_parser_billet    = None
_parser_passeport = None

def obtenir_parser_billet():
    global _parser_billet
    if _parser_billet is None:
        from analyse_traitement_av_regex import FlightTicketParser
        _parser_billet = FlightTicketParser(lang='fr')
    return _parser_billet

def obtenir_parser_passeport():
    global _parser_passeport
    if _parser_passeport is None:
        from analyse_traitement_pas_regex import GabonPassportParser
        _parser_passeport = GabonPassportParser(lang='fr')
    return _parser_passeport

def _extraire_dates_ocr(resultat_ocr):
    dates = []
    if not isinstance(resultat_ocr, dict):
        return dates
    
    valeurs_brutes = []
    if resultat_ocr.get('toutes_les_dates_detectees'):
        valeurs_brutes.extend(resultat_ocr.get('toutes_les_dates_detectees'))
    elif resultat_ocr.get('date_voyage'):
        valeurs_brutes.append(resultat_ocr.get('date_voyage'))
        
    mois_map = {
        'JAN': 1, 'JANV': 1, 'JANUARY': 1, 'FEB': 2, 'FEV': 2, 'FEBRUARY': 2,
        'MAR': 3, 'MARS': 3, 'MARCH': 3, 'APR': 4, 'AVR': 4, 'APRIL': 4,
        'MAY': 5, 'MAI': 5, 'JUN': 6, 'JUIN': 6, 'JUNE': 6,
        'JUL': 7, 'JUIL': 7, 'JULY': 7, 'AUG': 8, 'AOU': 8, 'AUGUST': 8,
        'SEP': 9, 'SEPTEMBER': 9, 'OCT': 10, 'OCTOBER': 10,
        'NOV': 11, 'NOVEMBER': 11, 'DEC': 12, 'DECEMBER': 12
    }

    for val in valeurs_brutes:
        val_str = str(val).strip().upper()
        date_parse = None

        for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d'):
            try:
                date_parse = datetime.strptime(val_str, fmt)
                break
            except ValueError:
                continue

        if not date_parse:
            match = re.search(r'(\d{1,2})\s*([A-Z]{3,10})\s*(\d{2,4})?', val_str)
            if match:
                jour = int(match.group(1))
                mois_str = match.group(2)
                annee_str = match.group(3)

                mois = None
                for cle_mois, num_mois in mois_map.items():
                    if cle_mois in mois_str:
                        mois = num_mois
                        break

                if mois:
                    annee = int(annee_str) if annee_str else datetime.now(timezone.utc).year
                    if annee < 100:
                        annee += 2000
                    try:
                        date_parse = datetime(annee, mois, jour)
                    except ValueError:
                        pass

        if date_parse:
            dates.append(date_parse)
            
    return dates

# =========================================================
# MODELES
# =========================================================

class Utilisateur(db.Model):
    id               = db.Column(db.Integer, primary_key=True) 
    nom              = db.Column(db.String(100), nullable=False) 
    prenom           = db.Column(db.String(100), nullable=False)
    email            = db.Column(db.String(150), unique=True, nullable=False)
    mot_de_passe     = db.Column(db.String(200))
    actif            = db.Column(db.Boolean, default=False)
    token_activation = db.Column(db.String(100), unique=True)
    role             = db.Column(db.String(20), default='client')
    date_creation    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    dossiers         = db.relationship('Dossier', backref='client', lazy=True)

class Dossier(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    reference         = db.Column(db.String(30), unique=True, nullable=False)
    type_dossier      = db.Column(db.String(20), nullable=False)
    periode           = db.Column(db.String(7))
    montant           = db.Column(db.Float, default=0.0)
    statut            = db.Column(db.String(20), default='incomplet')
    date_debut_voyage = db.Column(db.DateTime)
    date_fin_voyage   = db.Column(db.DateTime)
    commentaire_admin = db.Column(db.Text)
    a_ete_mis_a_jour  = db.Column(db.Boolean, default=False)
    date_creation     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    date_mise_a_jour  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    utilisateur_id    = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    lignes            = db.relationship('LigneTransaction', backref='dossier', lazy=True, cascade='all, delete-orphan')
    documents         = db.relationship('Document', backref='dossier', lazy=True, cascade='all, delete-orphan')

class LigneTransaction(db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    date_operation     = db.Column(db.DateTime)
    libelle            = db.Column(db.String(300), nullable=False)
    montant            = db.Column(db.Float, nullable=False)
    devise             = db.Column(db.String(10), default='XAF')
    dossier_id         = db.Column(db.Integer, db.ForeignKey('dossier.id'), nullable=False)
    justificatifs      = db.relationship('Document', backref='ligne', lazy=True, cascade='all, delete-orphan')

    @property
    def est_justifiee(self):
        return len(self.justificatifs) > 0

class Document(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nom_fichier   = db.Column(db.String(200), nullable=False)
    type_document = db.Column(db.String(30), nullable=False)
    chemin        = db.Column(db.String(300), nullable=False)
    donnees_ocr   = db.Column(db.Text)
    statut        = db.Column(db.String(20), default='en_attente')
    motif_refus   = db.Column(db.Text)
    date_upload   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    dossier_id    = db.Column(db.Integer, db.ForeignKey('dossier.id'), nullable=False)
    ligne_id      = db.Column(db.Integer, db.ForeignKey('ligne_transaction.id'))

# =========================================================
# DECORATEURS
# =========================================================

def login_requis(f):
    @wraps(f)
    def fonction_protegee(*args, **kwargs):
        if 'utilisateur_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return fonction_protegee

def admin_requis(f):
    @wraps(f)
    def fonction_protegee(*args, **kwargs):
        if 'utilisateur_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return fonction_protegee

# =========================================================
# LOGIQUE METIER & IMPORT EXCEL
# =========================================================

COL_EMAIL, COL_NOM, COL_DATE, COL_MONTANT, COL_MARCHAND, COL_PAYS = "EM_PAYCO_EMAIL", "NOM_PORTEUR", "DATE_TRANSACTION", "MONTANT_BILL", "MARCHAND", "PAYS"
COLS_REQUISES = (COL_EMAIL, COL_NOM, COL_DATE, COL_MONTANT)

MOIS = {'janvier': 1, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12}

def _sans_accents(texte):
    return ''.join(c for c in unicodedata.normalize('NFD', texte) if unicodedata.category(c) != 'Mn')

def _deviner_periode(nom_fichier):
    base = _sans_accents(os.path.basename(nom_fichier)).lower()
    mois_num = None
    for mois, numero in MOIS.items():
        if mois in base:
            mois_num = numero
            break
    m = re.search(r'(20\d{2}|_\d{2})', base)
    annee = m.group(1).lstrip('_') if m else None
    if annee and len(annee) == 2: annee = '20' + annee
    return f"{annee}-{mois_num:02d}" if mois_num and annee else None

def _separer_nom(nom_complet):
    parts = str(nom_complet).split()
    return (parts[0], ' '.join(parts[1:])) if len(parts) >= 2 else (parts[0] if parts else 'CLIENT', '')

def _lire_avec_entete(chemin):
    for h in (0, 1, 2, 3):
        try:
            df = pd.read_excel(chemin, header=h)
            if all(col in df.columns for col in COLS_REQUISES): return df
        except: continue
    return pd.read_csv(chemin) if chemin.endswith('.csv') else pd.read_excel(chemin)

def _importer_fichier(chemin, type_dossier, periode=None, base_url='http://127.0.0.1:5000'):
    df = _lire_avec_entete(chemin)
    
    if type_dossier == 'ligne' and not periode:
        periode = _deviner_periode(chemin)
        if not periode:
            periode = datetime.now().strftime('%Y-%m')

    manquantes = [c for c in COLS_REQUISES if c not in df.columns]
    if manquantes: raise ValueError(f"Colonnes introuvables : {', '.join(manquantes)}")

    df[COL_EMAIL] = df[COL_EMAIL].astype(str).str.strip().str.lower()
    df = df[df[COL_EMAIL].str.contains("@", na=False)].copy()
    
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    df[COL_DATE] = df[COL_DATE].apply(lambda x: x.replace(tzinfo=None) if pd.notna(x) else x)
    df[COL_MONTANT] = pd.to_numeric(df[COL_MONTANT], errors="coerce")

    df = df.sort_values(by=[COL_EMAIL, COL_DATE])
    df['CUMUL_CALCULE'] = df.groupby(COL_EMAIL)[COL_MONTANT].cumsum()

    resume = {"type": type_dossier, "periode": periode, "comptes_crees": 0, "comptes_existants": 0, "dossiers_crees": 0, "dossiers_actualises": 0, "dossiers_ignores": 0, "lignes": 0, "a_notifier": []}
    seuil = 5000000.0 if type_dossier == 'voyage' else 1000000.0

    for email, groupe in df.groupby(COL_EMAIL):
        lignes_depassement = groupe[groupe['CUMUL_CALCULE'] > seuil]

        if lignes_depassement.empty:
            continue

        nom_complet = str(groupe.iloc[0][COL_NOM]).strip()
        nom, prenom = _separer_nom(nom_complet)

        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if not utilisateur:
            utilisateur = Utilisateur(nom=nom, prenom=prenom, email=email, token_activation=secrets.token_urlsafe(24))
            db.session.add(utilisateur)
            db.session.commit()
            resume["comptes_crees"] += 1
        else:
            resume["comptes_existants"] += 1

        min_date = lignes_depassement[COL_DATE].min().to_pydatetime()
        dossier = None

        if type_dossier == 'voyage':
            candidats = Dossier.query.filter_by(utilisateur_id=utilisateur.id, type_dossier='voyage').all()
            for cand in candidats:
                if cand.date_debut_voyage and cand.date_fin_voyage:
                    if (cand.date_debut_voyage - timedelta(days=15)) <= min_date <= (cand.date_fin_voyage + timedelta(days=15)):
                        dossier = cand
                        break
                elif cand.statut in ('incomplet', 'en_attente', 'en_cours'):
                    dossier = cand
                    break
            if not dossier:
                ref = f"DOC-{min_date.year}-VY{uuid.uuid4().hex[:5].upper()}"
                dossier = Dossier(reference=ref, type_dossier='voyage', periode=min_date.strftime('%Y-%m'), montant=0.0, statut='incomplet', utilisateur_id=utilisateur.id)
                db.session.add(dossier)
                resume["dossiers_crees"] += 1
            else:
                if dossier.statut in ('valide', 'refuse'): dossier.statut = 'incomplet'
                resume["dossiers_actualises"] += 1

        else:
            dossier = Dossier.query.filter_by(utilisateur_id=utilisateur.id, type_dossier='ligne', periode=periode).first()
            if not dossier:
                ref = f"DOC-{(periode or '2026')[:4]}-LN{uuid.uuid4().hex[:5].upper()}"
                dossier = Dossier(reference=ref, type_dossier='ligne', periode=periode, montant=0.0, statut='incomplet', utilisateur_id=utilisateur.id)
                db.session.add(dossier)
                resume["dossiers_crees"] += 1
            else:
                if dossier.statut in ('valide', 'refuse'): dossier.statut = 'incomplet'
                resume["dossiers_actualises"] += 1
        
        db.session.commit()

        existing_lines = {(l.date_operation.strftime('%Y-%m-%d') if l.date_operation else '', l.libelle, l.montant) for l in dossier.lignes}
        nouvelles_lignes = 0

        for _, row in lignes_depassement.iterrows():
            m, p = str(row.get(COL_MARCHAND, '')).strip(), str(row.get(COL_PAYS, '')).strip()
            lib = m if m and m.lower() != 'nan' else "Transaction"
            if p and p.lower() != 'nan': lib = f"{lib} - {p}"
            date_op = row[COL_DATE].to_pydatetime() if pd.notna(row[COL_DATE]) else None
            mnt = float(row[COL_MONTANT]) if pd.notna(row[COL_MONTANT]) else 0.0
            
            key = (date_op.strftime('%Y-%m-%d') if date_op else '', lib, mnt)
            if key not in existing_lines:
                db.session.add(LigneTransaction(date_operation=date_op, libelle=lib[:300], montant=mnt, dossier_id=dossier.id))
                existing_lines.add(key)
                nouvelles_lignes += 1
                resume["lignes"] += 1
                dossier.montant += mnt

        db.session.commit()

        if nouvelles_lignes > 0:
            lien = f"{base_url}/activer/{utilisateur.token_activation}" if not utilisateur.actif else f"{base_url}/login"
            resume["a_notifier"].append({"email": email, "nom": nom_complet, "lien": lien, "actif": utilisateur.actif, "nb": nouvelles_lignes, "reference": dossier.reference})

    return resume

# =========================================================
# ROUTES — AUTH & ACTIVATION
# =========================================================

@app.route('/')
def accueil(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'utilisateur_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('role') == 'admin' else 'dashboard'))
    erreur = None
    if request.method == 'POST':
        u = Utilisateur.query.filter_by(email=request.form.get('email')).first()
        if u and not u.actif: erreur = "Compte inactif. Utilisez le lien reçu par email."
        elif u and u.mot_de_passe and check_password_hash(u.mot_de_passe, request.form.get('mot_de_passe')):
            session['utilisateur_id'], session['utilisateur_nom'], session['role'] = u.id, u.prenom, u.role
            return redirect(url_for('admin_dashboard' if u.role == 'admin' else 'dashboard'))
        else: erreur = 'Email ou mot de passe incorrect.'
    return render_template('login.html', erreur=erreur)

@app.route('/activer/<token>', methods=['GET', 'POST'])
def activer(token):
    u = Utilisateur.query.filter_by(token_activation=token).first()
    if not u: return render_template('activer.html', token=None, erreur=None, email=None)
    erreur = None
    if request.method == 'POST':
        mdp, conf = request.form.get('mot_de_passe'), request.form.get('confirmation')
        if len(mdp) < 6: erreur = '6 caractères minimum.'
        elif mdp != conf: erreur = 'Les mots de passe ne correspondent pas.'
        else:
            u.mot_de_passe, u.actif, u.token_activation = generate_password_hash(mdp), True, None
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('activer.html', token=token, erreur=erreur, email=u.email)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================================================
# ROUTES — CLIENT
# =========================================================

@app.route('/dashboard')
@login_requis
def dashboard():
    u = Utilisateur.query.get(session['utilisateur_id'])
    if not u:
        session.clear()
        return redirect(url_for('login'))
    tous = Dossier.query.filter_by(utilisateur_id=u.id).order_by(Dossier.date_creation.desc()).all()
    dossiers = [d for d in tous if d.statut not in ('valide', 'refuse')]
    archives = [d for d in tous if d.statut in ('valide', 'refuse')]
    return render_template('dashboard.html', utilisateur=u, dossiers=dossiers, archives=archives)

@app.route('/dossier/anticiper-voyage', methods=['POST'])
@login_requis
def anticiper_voyage():
    ref = f"DOC-{datetime.now(timezone.utc).year}-VY{uuid.uuid4().hex[:5].upper()}"
    nouveau_voyage = Dossier(reference=ref, type_dossier='voyage', statut='incomplet', utilisateur_id=session['utilisateur_id'], montant=0.0)
    db.session.add(nouveau_voyage)
    db.session.commit()
    flash("Nouveau voyage cree. Vous pouvez y deposer vos documents.", "ok")
    return redirect(url_for('detail_dossier', dossier_id=nouveau_voyage.id))

def _docs_dossier(dossier):
    return {d.type_document: d for d in dossier.documents if d.ligne_id is None}

def _recalculer_statut(dossier):
    if dossier.statut in ('valide', 'refuse'): return
    par_type = _docs_dossier(dossier)
    
    lignes_ok = True
    if dossier.lignes:
        lignes_ok = all(l.justificatifs and not any(j.statut == 'refuse' for j in l.justificatifs) for l in dossier.lignes)

    if dossier.type_dossier == 'voyage':
        passeport_ok = 'passeport' in par_type and par_type['passeport'].statut != 'refuse'
        billet_ok = ('billet_aller' in par_type and par_type['billet_aller'].statut != 'refuse') or ('billet_retour' in par_type and par_type['billet_retour'].statut != 'refuse')
        dossier.statut = 'en_attente' if (lignes_ok and passeport_ok and billet_ok) else 'incomplet'
    else:
        dossier.statut = 'en_attente' if lignes_ok and dossier.lignes else 'incomplet'

@app.route('/dossier/<int:dossier_id>')
@login_requis
def detail_dossier(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    if dossier.utilisateur_id != session['utilisateur_id']: return redirect(url_for('dashboard'))
    
    par_type = _docs_dossier(dossier)
    lignes = sorted(dossier.lignes, key=lambda l: (l.date_operation or datetime.min))
    nb_a_justifier = sum(1 for l in lignes if not l.est_justifiee or any(j.statut == 'refuse' for j in l.justificatifs))
    
    return render_template(
        'detail_dossier.html', dossier=dossier, lignes=lignes, par_type=par_type,
        nb_a_justifier=nb_a_justifier, modifiable=dossier.statut in ('incomplet', 'en_attente', 'en_cours'),
        icones={'passeport': 'ID', 'billet_aller': 'AV', 'billet_retour': 'AV'}
    )

def tache_ocr_background(app, doc_id, champ):
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc: return
        dossier = doc.dossier
        chemin_absolu = os.path.abspath(doc.chemin)
        statut_doc, motif = 'en_attente', None
        donnees_ocr_json = None
        
        try:
            if champ == 'passeport':
                res = obtenir_parser_passeport().process_document(chemin_absolu)
                if res:
                    donnees_ocr_json = json.dumps(res, ensure_ascii=False)
                    if res.get('date_expiration'):
                        try:
                            d_exp = datetime.strptime(res['date_expiration'], '%d.%m.%Y')
                            if d_exp < datetime.now(): 
                                statut_doc, motif = 'refuse', f"Expiré depuis le {res['date_expiration']}"
                            else: 
                                statut_doc = 'valide'
                        except: pass
                    else: 
                        statut_doc, motif = 'refuse', "Date d'expiration illisible par l'IA."
                else: 
                    statut_doc, motif = 'refuse', "Passeport non détecté (chemin introuvable ou image trop floue)."
                    
            elif champ in ('billet_aller', 'billet_retour'):
                res = obtenir_parser_billet().traiter_document(chemin_absolu)
                if res:
                    donnees_ocr_json = json.dumps(res, ensure_ascii=False)
                    dates_tr = _extraire_dates_ocr(res)
                    if dates_tr:
                        m_bil = min(dates_tr).replace(tzinfo=None)
                        d_trans = [l.date_operation.replace(tzinfo=None) for l in dossier.lignes if l.date_operation]
                        
                        if d_trans and m_bil > min(d_trans): 
                            statut_doc, motif = 'refuse', "Dates de vol postérieures aux transactions."
                        else: 
                            statut_doc = 'valide'
                        
                        toutes_dates_ocr = [d.replace(tzinfo=None) for d in dates_tr]
                        for d in dossier.documents:
                            if d.id != doc.id and d.donnees_ocr and d.type_document.startswith('billet'):
                                try:
                                    data = json.loads(d.donnees_ocr)
                                    toutes_dates_ocr.extend([dt.replace(tzinfo=None) for dt in _extraire_dates_ocr(data)])
                                except: pass
                        if toutes_dates_ocr:
                            dossier.date_debut_voyage = min(toutes_dates_ocr)
                            dossier.date_fin_voyage = max(toutes_dates_ocr)
                            dossier.periode = dossier.date_debut_voyage.strftime('%Y-%m')
                    else: 
                        statut_doc, motif = 'refuse', "Aucune date de voyage lisible sur ce billet."
                else: 
                    statut_doc, motif = 'refuse', "Billet non détecté (chemin introuvable ou format non reconnu)."
                    
        except Exception as e: 
            statut_doc, motif = 'refuse', f"Erreur système IA : {str(e)}"

        doc.statut, doc.motif_refus, doc.donnees_ocr = statut_doc, motif, donnees_ocr_json
        db.session.commit()
        _recalculer_statut(dossier)
        dossier.date_mise_a_jour = datetime.now(timezone.utc)
        db.session.commit()

# --- NOUVELLE ROUTE POUR L'UPLOAD AJAX ---
@app.route('/dossier/<int:dossier_id>/upload_async', methods=['POST'])
@login_requis
def upload_async(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    if dossier.utilisateur_id != session['utilisateur_id'] or dossier.statut not in ('incomplet', 'en_attente', 'en_cours'):
        return jsonify({'erreur': 'Non autorisé'}), 403

    champ = request.form.get('type_document')
    f = request.files.get('file')

    if not f or not extension_valide(f.filename):
        return jsonify({'erreur': 'Fichier invalide ou format non supporté'}), 400

    if champ not in ('passeport', 'billet_aller', 'billet_retour'):
        return jsonify({'erreur': 'Type de document invalide'}), 400

    rep = chemin_dossier_upload(dossier.utilisateur_id, dossier.reference)
    par_type = _docs_dossier(dossier)
    
    if champ in par_type:
        try: os.remove(par_type[champ].chemin)
        except: pass
        db.session.delete(par_type[champ])
        db.session.commit()

    chemin = os.path.join(rep, f"{champ}_{secure_filename(f.filename)}")
    f.save(chemin)
    
    doc = Document(nom_fichier=os.path.basename(chemin), type_document=champ, chemin=chemin, dossier_id=dossier.id)
    db.session.add(doc)
    dossier.a_ete_mis_a_jour = True
    db.session.commit()
    
    if est_image(doc.nom_fichier):
        threading.Thread(target=tache_ocr_background, args=(app, doc.id, champ)).start()

    _recalculer_statut(dossier)
    dossier.date_mise_a_jour = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({'message': 'Document reçu', 'doc_id': doc.id})

@app.route('/dossier/<int:dossier_id>/justifier', methods=['POST'])
@login_requis
def justifier_dossier(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    if dossier.utilisateur_id != session['utilisateur_id'] or dossier.statut not in ('incomplet', 'en_attente', 'en_cours'):
        return redirect(url_for('dashboard'))

    rep = chemin_dossier_upload(dossier.utilisateur_id, dossier.reference)
    par_type = _docs_dossier(dossier)
    maj = False

    if dossier.type_dossier == 'voyage':
        if not (dossier.date_debut_voyage and dossier.date_fin_voyage):
            d_aller_manuelle = request.form.get('date_aller_manuelle')
            d_retour_manuelle = request.form.get('date_retour_manuelle')
            if d_aller_manuelle:
                try: 
                    dossier.date_debut_voyage = datetime.strptime(d_aller_manuelle, '%Y-%m-%d')
                    dossier.periode = dossier.date_debut_voyage.strftime('%Y-%m')
                except ValueError: pass
            if d_retour_manuelle:
                try: dossier.date_fin_voyage = datetime.strptime(d_retour_manuelle, '%Y-%m-%d')
                except ValueError: pass

        # Les documents voyage peuvent encore être traités ici si on utilise le formulaire classique
        for champ in ('passeport', 'billet_aller', 'billet_retour'):
            f = request.files.get(champ)
            if not f or not extension_valide(f.filename): continue
            if champ in par_type:
                try: os.remove(par_type[champ].chemin)
                except: pass
                db.session.delete(par_type[champ])
            chemin = os.path.join(rep, f"{champ}_{secure_filename(f.filename)}")
            f.save(chemin)
            doc = Document(nom_fichier=os.path.basename(chemin), type_document=champ, chemin=chemin, dossier_id=dossier.id)
            db.session.add(doc)
            db.session.commit()
            if est_image(doc.nom_fichier): threading.Thread(target=tache_ocr_background, args=(app, doc.id, champ)).start()
            maj = True

    for ligne in dossier.lignes:
        f = request.files.get(f'justif_{ligne.id}')
        if not f or not extension_valide(f.filename): continue
        for d in ligne.justificatifs:
            try: os.remove(d.chemin)
            except: pass
            db.session.delete(d)
        chemin = os.path.join(rep, f"justif_ligne{ligne.id}_{secure_filename(f.filename)}")
        f.save(chemin)
        db.session.add(Document(nom_fichier=os.path.basename(chemin), type_document='justificatif', chemin=chemin, dossier_id=dossier.id, ligne_id=ligne.id))
        maj = True

    if maj: dossier.a_ete_mis_a_jour = True
    db.session.commit()
    _recalculer_statut(dossier)
    dossier.date_mise_a_jour = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for('detail_dossier', dossier_id=dossier.id))

@app.route('/document/<int:document_id>')
@login_requis
def voir_document(document_id):
    doc = Document.query.get_or_404(document_id)
    if session.get('role') != 'admin' and doc.dossier.utilisateur_id != session['utilisateur_id']: return redirect(url_for('dashboard'))
    return send_file(os.path.abspath(doc.chemin)) if os.path.exists(doc.chemin) else ("Fichier introuvable", 404)

# =========================================================
# ROUTES - ADMIN
# =========================================================

@app.route('/admin')
@admin_requis
def admin_dashboard():
    f_statut, f_type = request.args.get('statut', ''), request.args.get('type', '')
    req = Dossier.query.filter(~Dossier.statut.in_(('valide', 'refuse')))
    if f_statut: req = req.filter_by(statut=f_statut)
    if f_type: req = req.filter_by(type_dossier=f_type)
    tous = Dossier.query.all()
    stats = {
        'actifs': sum(1 for d in tous if d.statut not in ('valide', 'refuse')),
        'incomplets': sum(1 for d in tous if d.statut == 'incomplet'),
        'en_attente': sum(1 for d in tous if d.statut == 'en_attente'),
        'en_cours': sum(1 for d in tous if d.statut == 'en_cours'),
        'archives': sum(1 for d in tous if d.statut in ('valide', 'refuse'))
    }
    return render_template('admin_dashboard.html', dossiers=req.order_by(Dossier.date_creation.desc()).all(), stats=stats, filtre_statut=f_statut, filtre_type=f_type)

@app.route('/admin/archive')
@admin_requis
def admin_archive():
    fins = Dossier.query.filter(Dossier.statut.in_(('valide', 'refuse'))).order_by(Dossier.date_mise_a_jour.desc()).all()
    par_client = {}
    for d in fins: par_client.setdefault(d.utilisateur_id, {'client': d.client, 'dossiers': []})['dossiers'].append(d)
    return render_template('admin_archive.html', groupes=sorted(par_client.values(), key=lambda g: g['client'].nom), total=len(fins))

@app.route('/admin/import', methods=['GET', 'POST'])
@admin_requis
def admin_import():
    resume, erreur = None, None
    if request.method == 'POST':
        fichier, type_d, periode = request.files.get('fichier_excel'), request.form.get('type_dossier'), request.form.get('periode', '').strip() or None
        if not fichier or not fichier.filename.endswith(('.xlsx', '.xls', '.csv')): erreur = "Fichier non pris en charge."
        else:
            rep = os.path.join(app.config['UPLOAD_FOLDER'], '_imports')
            os.makedirs(rep, exist_ok=True)
            chemin = os.path.join(rep, secure_filename(fichier.filename))
            fichier.save(chemin)
            try: resume = _importer_fichier(chemin, type_d, periode, app.config.get('BASE_URL'))
            except Exception as e: erreur = f"Erreur import : {e}"
    return render_template('admin_import.html', resume=resume, erreur=erreur, clients=Utilisateur.query.filter_by(role='client').all())

@app.route('/admin/dossier/<int:dossier_id>')
@admin_requis
def admin_detail_dossier(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    if dossier.a_ete_mis_a_jour: dossier.a_ete_mis_a_jour = False; db.session.commit()
    docs_v = sorted(_docs_dossier(dossier).values(), key=lambda d: {'passeport': 0, 'billet_aller': 1, 'billet_retour': 2}.get(d.type_document, 9))
    ocr_p = {d.id: json.loads(d.donnees_ocr) for d in docs_v if d.donnees_ocr}
    return render_template('admin_detail_dossier.html', dossier=dossier, lignes=sorted(dossier.lignes, key=lambda l: l.date_operation or datetime.min), docs_voyage=docs_v, ocr_par_doc=ocr_p)

@app.route('/admin/dossier/<int:dossier_id>/modifier-dates', methods=['POST'])
@admin_requis
def modifier_dates_voyage(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    try:
        if request.form.get('date_debut'): 
            dossier.date_debut_voyage = datetime.strptime(request.form.get('date_debut'), '%Y-%m-%d')
            dossier.periode = dossier.date_debut_voyage.strftime('%Y-%m')
        if request.form.get('date_fin'): 
            dossier.date_fin_voyage = datetime.strptime(request.form.get('date_fin'), '%Y-%m-%d')
        db.session.commit()
    except: pass
    return redirect(url_for('admin_detail_dossier', dossier_id=dossier.id))

@app.route('/admin/document/<int:document_id>/decision', methods=['POST'])
@admin_requis
def admin_document_decision(document_id):
    doc = Document.query.get_or_404(document_id)
    if request.form.get('action') == 'valider': doc.statut, doc.motif_refus = 'valide', None
    else: doc.statut, doc.motif_refus = 'refuse', request.form.get('motif_refus', '').strip() or "Non conforme"
    db.session.commit(); _recalculer_statut(doc.dossier); db.session.commit()
    return redirect(url_for('admin_detail_dossier', dossier_id=doc.dossier_id))

@app.route('/admin/dossier/<int:dossier_id>/decision', methods=['POST'])
@admin_requis
def decision_dossier(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    act = request.form.get('action')
    if act == 'prendre_en_charge': dossier.statut = 'en_cours'
    elif act in ('valider', 'refuse'): dossier.statut = act
    if request.form.get('commentaire'): dossier.commentaire_admin = request.form.get('commentaire').strip()
    db.session.commit()
    return redirect(url_for('admin_detail_dossier', dossier_id=dossier.id))

@app.route('/admin/dossier/<int:dossier_id>/supprimer', methods=['POST'])
@admin_requis
def supprimer_dossier(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    shutil.rmtree(chemin_dossier_upload(dossier.utilisateur_id, dossier.reference), ignore_errors=True)
    db.session.delete(dossier); db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/utilisateurs')
@admin_requis
def admin_utilisateurs():
    return render_template('admin_utilisateurs.html', admins=Utilisateur.query.filter_by(role='admin').all(), nb_clients=Utilisateur.query.filter_by(role='client').count(), moi=session['utilisateur_id'])

@app.route('/admin/utilisateurs/creer', methods=['POST'])
@admin_requis
def creer_admin():
    nom          = (request.form.get('nom') or '').strip()
    prenom       = (request.form.get('prenom') or '').strip()
    email        = (request.form.get('email') or '').strip().lower()
    mot_de_passe = request.form.get('mot_de_passe') or ''

    if not nom or not prenom or not email:
        flash("Nom, prenom et email sont obligatoires.", 'erreur')
    elif len(mot_de_passe) < 6:
        flash("Le mot de passe doit contenir au moins 6 caracteres.", 'erreur')
    elif Utilisateur.query.filter_by(email=email).first():
        flash("Un compte existe deja avec cet email.", 'erreur')
    else:
        db.session.add(Utilisateur(
            nom=nom, prenom=prenom, email=email,
            mot_de_passe=generate_password_hash(mot_de_passe),
            actif=True, role='admin'
        ))
        db.session.commit()
        flash(f"Administrateur {prenom} {nom} cree.", 'ok')
    return redirect(url_for('admin_utilisateurs'))

def _nb_admins_actifs():
    return Utilisateur.query.filter_by(role='admin', actif=True).count()

@app.route('/admin/utilisateurs/<int:utilisateur_id>/basculer', methods=['POST'])
@admin_requis
def basculer_admin(utilisateur_id):
    cible = Utilisateur.query.get_or_404(utilisateur_id)
    if cible.role != 'admin': flash("Action reservee aux administrateurs.", 'erreur')
    elif cible.id == session['utilisateur_id']: flash("Vous ne pouvez pas modifier votre propre compte.", 'erreur')
    elif cible.actif and _nb_admins_actifs() <= 1: flash("Impossible : il doit rester au moins un administrateur actif.", 'erreur')
    else:
        cible.actif = not cible.actif
        db.session.commit()
        etat = "active" if cible.actif else "desactive"
        flash(f"Compte de {cible.prenom} {cible.nom} {etat}.", 'ok')
    return redirect(url_for('admin_utilisateurs'))

@app.route('/admin/utilisateurs/<int:utilisateur_id>/supprimer', methods=['POST'])
@admin_requis
def supprimer_admin(utilisateur_id):
    cible = Utilisateur.query.get_or_404(utilisateur_id)
    if cible.role != 'admin': flash("Action reservee aux administrateurs.", 'erreur')
    elif cible.id == session['utilisateur_id']: flash("Vous ne pouvez pas supprimer votre propre compte.", 'erreur')
    elif cible.actif and _nb_admins_actifs() <= 1: flash("Impossible : il doit rester au moins un administrateur actif.", 'erreur')
    else:
        nom = f"{cible.prenom} {cible.nom}"
        db.session.delete(cible)
        db.session.commit()
        flash(f"Administrateur {nom} supprime.", 'ok')
    return redirect(url_for('admin_utilisateurs'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context(): db.create_all()
    app.run(
        debug=True,
        use_reloader=False,
        exclude_patterns=[
            '*/site-packages/*',
            '*/paddle/*',
            '*/paddlex/*',
        ]
    )