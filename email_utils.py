# email_utils.py
"""
Module pour la gestion de l'envoi d'emails
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class EmailSender:
    """Classe pour gérer l'envoi d'emails avec pièces jointes"""
    
    def __init__(self, sender_email, password, smtp_server="smtp.gmail.com", smtp_port=587):
        """
        Initialise le gestionnaire d'emails
        
        Args:
            sender_email: Email de l'expéditeur
            password: Mot de passe d'application
            smtp_server: Serveur SMTP (défaut: Gmail)
            smtp_port: Port SMTP (défaut: 587)
        """
        self.sender_email = sender_email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_