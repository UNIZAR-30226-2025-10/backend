from flask import Flask, redirect, render_template, request, session, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from db.models import *
from utils.hash import hash, verify
from flask_mail import Mail, Message
from db.db import get_db
import os
import random

app = Flask(__name__)

# Clave secreta para firmar los tokens JWT
app.config["JWT_SECRET_KEY"] = "supersecreto"
jwt = JWTManager(app)

# Configurar correo para enviar codigo de restablecimiento de contraseña
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = data.get("correo")
    nombreUsuario = data.get("nombreUsuario")
    contrasenya = data.get("contrasenya")
    
    if not contrasenya:
        return jsonify({"error": "Falta la contraseña."}), 400
    if not correo and not nombreUsuario:
        return jsonify({"error": "Falta el nombre de usario o correo."}), 400
              
    try:
        with closing(next(get_db())) as db:
            if nombreUsuario:
                usuario = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
            elif correo:
                usuario = db.get(Usuario, correo)
            
            if usuario and verify(contrasenya, usuario.contrasenya):
                access_token = create_access_token(identity=usuario.correo)
                return jsonify({"token": access_token,
                                "usuario": usuario.to_dict()}), 200 
            else:
                return jsonify({"message": "Credenciales incorrectas."}), 401
    
    except Exception as e:
        return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

@app.route("/register-oyente", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = data.get("correo")
    nombreUsuario = data.get("nombreUsuario")
    contrasenya = data.get("contrasenya")

    if not correo or not nombreUsuario or not contrasenya:
        return jsonify({"error": "Faltan campos"}), 400
              
    try:
        with closing(next(get_db())) as db:
            correo_existente = db.get(Usuario, correo)
            if correo_existente:
                return jsonify({"error": "El correo {correo_existente.correo} ya está en uso."}), 400
                        
            nombreUsuario_existente = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
            if nombreUsuario_existente:
                return jsonify({"error": "El nombre de usuario {nombreUsuario_existente.nombreUsuario} ya está en uso."}), 400

            contrasenyaHash = hash(contrasenya)           
            usuario = Usuario(correo=correo, nombreUsuario=nombreUsuario,
                              contrasenya=contrasenyaHash, fotoPerfil="DEFAULT",
                              volumen=100, tipo="oyente")
            db.add(usuario) 
            db.commit() 
            access_token = create_access_token(identity=usuario.correo)
            return jsonify({"token": access_token,
                            "usuario": usuario.to_dict()}), 200 
               
    except Exception as e:
        return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

@app.route('/verify-artista', methods=['POST'])
def verify_artista():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    correo = data.get("correo")
    token = data.get("token")

    if not correo or not token:
        return jsonify({"error": "Faltan datos"}), 400

    db = next(get_db())
    reset_entry = db.query(Pendiente).filter_by(Usuario_correo=correo, codigo=token).first()

    if not reset_entry:
        return jsonify({"error": "Token inválido"}), 400
    
    # Si el token es valido, eliminarlo
    db.delete(reset_entry)
    try:
        db.commit()
        access_token = create_access_token(identity=usuario.correo)
        return jsonify({"token": access_token,
                            "usuario": usuario.to_dict()}), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "Error al eliminar el token"}), 500    

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    correo = data.get("correo")
              
    db = next(get_db())
    if correo:
        usuario = db.get(Usuario, correo)
    else:
        return jsonify({"error": "Falta el correo"}), 500
    
    if not usuario:
        return jsonify({"error": "El correo no está registrado"}), 400

    # Generar un token numerico aleatorio de 6 digitos
    token = str(random.randint(100000, 999999))

            # Crear nueva entrada en la tabla ContraReset
    reset_entry = ContraReset(Usuario_correo=correo, token=token)
    db.session.add(reset_entry)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Error al guardar el token"}), 500

    # Enviar correo con el token
    sender_email = app.config["MAIL_USERNAME"]
    msg = Message("Recuperación de contraseña", sender=sender_email, recipients=[correo])
    msg.body = f"Tu código de recuperación de contraseña es: {token}. Vuelve a la aplicación e introdúcelo."
    mail.send(msg)

    return 200

@app.route('/verify-token', methods=['POST'])
def verify_token():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    correo = data.get("correo")
    token = data.get("token")

    if not correo or not token:
        return jsonify({"error": "Faltan datos"}), 400

    db = next(get_db())
    reset_entry = db.query(ContraReset).filter_by(Usuario_correo=correo, token=token).first()

    if not reset_entry:
        return jsonify({"error": "Token inválido"}), 400
    
    # Si el token es valido, eliminarlo
    db.delete(reset_entry)
    try:
        db.commit()
        session["reset_password_user"] = correo  # Guardar usuario autorizado en sesion
    except Exception:
        db.rollback()
        return jsonify({"error": "Error al eliminar el token"}), 500

    return 200

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    correo = data.get("correo")
    nueva_contraseña = data.get("nueva_contraseña")

    if not correo or not nueva_contraseña:
        return jsonify({"error": "Faltan datos"}), 400
    
    # Verificar si el usuario realmente valido su token
    if session.get("reset_password_user") != correo:
        return jsonify({"error": "No tienes permiso para cambiar la contraseña"}), 403

    db = next(get_db())

    # Buscar al usuario en la base de datos
    usuario = db.query(Usuario).filter_by(correo=correo).first()

    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 400

    # Actualizar la contraseña del usuario con un hash seguro
    usuario.contrasenya = hash(nueva_contraseña)

    try:
        db.commit()
        return jsonify({"message": "Contraseña cambiada con éxito."}), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "Error al actualizar la contraseña"}), 500
