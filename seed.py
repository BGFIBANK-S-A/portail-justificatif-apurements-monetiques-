# -*- coding: utf-8 -*-
"""
Script de donnees de test (en attendant le parser Excel de la Phase C).
Lance :  python seed.py
Cree un admin, deux clients, et des dossiers pre-remplis de lignes.
"""
from datetime import datetime
import secrets
import token

from app import app, db, Utilisateur, Dossier, LigneTransaction


def creer_dossier(client, type_dossier, periode, reference, lignes):
    montant = sum(m for (_, _, m) in lignes)
    dossier = Dossier(
        reference=reference, type_dossier=type_dossier,
        periode=periode, montant=montant, statut='incomplet',
        utilisateur_id=client.id
    )
    db.session.add(dossier)
    db.session.commit()
    for (date_op, libelle, montant_ligne) in lignes:
        db.session.add(LigneTransaction(
            date_operation=date_op, libelle=libelle,
            montant=montant_ligne, devise='XAF', dossier_id=dossier.id
        ))
    db.session.commit()
    return dossier


with app.app_context():
    db.drop_all()
    db.create_all()

    # ---------- ADMIN (actif, mot de passe connu) ----------
    admin = Utilisateur(
        nom='SYSTEME', prenom='Admin',
        email='admin@bgfi.ga',
        mot_de_passe=None, actif=False, role='admin'
    )
    from werkzeug.security import generate_password_hash
    admin.mot_de_passe = generate_password_hash('admin123')
    admin.actif = True
    db.session.add(admin)



    db.session.commit()

    print('=' * 60)
    print('ADMIN    : admin@bgfi.ga / admin123')
    print('=' * 60)
