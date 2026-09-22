"""Envoi d'emails (activation de compte, notification de justification
requise). Si SMTP_HOST n'est pas configure, le message est simplement
affiche en console (utile en developpement)."""
import smtplib
from email.mime.text import MIMEText

from django.conf import settings


def envoyer_email(destinataire, sujet, corps):
    if not settings.SMTP_HOST:
        print("--- EMAIL (console, SMTP non configure) ---")
        print(f"A : {destinataire}\nSujet : {sujet}\n\n{corps}")
        print("--- FIN EMAIL ---")
        return

    message = MIMEText(corps, "plain", "utf-8")
    message["Subject"] = sujet
    message["From"] = settings.SMTP_FROM
    message["To"] = destinataire

    classe_smtp = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    with classe_smtp(settings.SMTP_HOST, settings.SMTP_PORT) as serveur:
        if not settings.SMTP_USE_SSL:
            serveur.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            serveur.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        serveur.sendmail(settings.SMTP_FROM, [destinataire], message.as_string())
