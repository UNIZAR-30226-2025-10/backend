from flask import Flask
from flask_mail import Mail, Message
import os

# Crear una instancia sin asociarla aun
mail = Mail()

"""Inicializa la configuración de Flask-Mail en la app."""
def init_mail(app):
    # Configurar correo para enviar codigo de restablecimiento de contraseña
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get('MAIL_USERNAME')

    # Asociar mail a la app
    mail.init_app(app)

"""Envía un correo usando Flask-Mail"""
def send_mail(destinatario, asunto, mensaje):
    msg = Message(asunto, recipients=[destinatario], body=mensaje)
    mail.send(msg)
         