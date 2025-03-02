from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from db.db import get_db
from db.models import *
from utils.hash import hash, verify
from utils.code import new_code
from utils.mail import send_mail
from utils.decorators import roles_required, tokenVersion_required
from datetime import timedelta

auth_bp = Blueprint('auth', __name__) 


"""Inicia sesion en la app"""
@auth_bp.route("/login", methods=["POST"])
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

    with get_db() as db:
        if nombreUsuario:
            usuario = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
        elif correo:
            usuario = db.get(Usuario, correo)
                
        if not usuario:
            return jsonify({"error": "Nombre de usuario o correo no válido."}), 401
        if not verify(contrasenya, usuario.contrasenya):
            return jsonify({"error": "Contraseña incorrecta."}), 401
        
        usuario_dict=usuario.to_dict()
    access_token = create_access_token(identity=usuario.correo, 
                                       additional_claims={"tokenVersion": usuario.tokenVersion,
                                                          "tipo": usuario.tipo},
                                       expires_delta=timedelta(hours=1))

    # Si es otro tipo de usuario, solo devuelve el token
    return jsonify({"token": access_token, "usuario":usuario_dict}), 200 


"""Crea una cuenta de oyente en la app"""
@auth_bp.route("/register-oyente", methods=["POST"])
def register_oyente():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = data.get("correo")
    nombreUsuario = data.get("nombreUsuario")
    contrasenya = data.get("contrasenya")

    if not correo or not nombreUsuario or not contrasenya:
        return jsonify({"error": "Faltan campos"}), 400
              
    with get_db() as db:
        correo_entry = db.get(Usuario, correo)
        if correo_entry:
            return jsonify({"error": f"El correo {correo_entry.correo} ya está en uso."}), 409
                    
        nombreUsuario_entry = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
        if nombreUsuario_entry:
            return jsonify({"error": f"El nombre de usuario {nombreUsuario_entry.nombreUsuario} ya está en uso."}), 409

        contrasenyaHash = hash(contrasenya)           
        oyente = Oyente(correo=correo, nombreUsuario=nombreUsuario,
                            contrasenya=contrasenyaHash, fotoPerfil="DEFAULT",
                            volumen=50, tokenVersion=1)
        db.add(oyente) 
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    access_token = create_access_token(identity=oyente.correo,
                                       additional_claims={"tokenVersion": 1,
                                                          "tipo": "oyente"},
                                       expires_delta=timedelta(hours=1))
    return jsonify({"token": access_token, "oyente": oyente.to_dict()}), 201 


"""Crea una cuenta de artista pendiente de validacion en la app"""
@auth_bp.route("/register-artista", methods=["POST"])
def register_artista():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400

    # Recuperar campos peticion
    correo = data.get("correo")
    nombreUsuario = data.get("nombreUsuario")
    contrasenya = data.get("contrasenya")
    nombreArtistico = data.get("nombreArtistico")
    if not correo or not nombreUsuario or not contrasenya or not nombreArtistico:
        return jsonify({"error": "Faltan campos en la petición."}), 400  
    
    with get_db() as db:
        # Comprobar correo no existe
        correo_entry = db.get(Usuario, correo)
        if correo_entry:
            return jsonify({"error": f"El correo {correo_entry.correo} ya está en uso."}), 400
        # Comprobar nombreUsuario no existe
        nombreUsuario_entry = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
        if nombreUsuario_entry:
            return jsonify({"error": f"El nombre de usuario {nombreUsuario_entry.nombreUsuario} ya está en uso."}), 400

        # Insertar usuario pendiente de validacion
        contrasenyaHash = hash(contrasenya)           
        pendiente = Pendiente(correo=correo, nombreUsuario=nombreUsuario,
                              contrasenya=contrasenyaHash, nombreArtistico=nombreArtistico,
                              tokenVersion=1)
        db.add(pendiente) 
        try:
            db.commit() 
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
        pendiente_dict=pendiente.to_dict()
        access_token = create_access_token(identity=pendiente.correo,
                                       additional_claims={"tokenVersion": 1,
                                                          "tipo": "pendiente"},
                                       expires_delta=timedelta(hours=1))

    return jsonify({"token": access_token, "pendiente": pendiente_dict}), 200


"""Verifica el codigo de validacion de una cuenta de artista y la crea en la app"""
@auth_bp.route('/verify-artista', methods=['POST'])
@jwt_required()
@tokenVersion_required()
@roles_required("valido")
def verify_artista():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    codigo = data.get("codigo")
    if not codigo:
        return jsonify({"error": "Faltan datos en la petición."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        # Comprobar que es valido
        valid_user = db.get(Valido, correo)
        if not valid_user:
            return jsonify({"error": "Correo no existe."}), 400
        
        # Comprobar codigo correcto
        if not verify(codigo, valid_user.codigo):
            return jsonify({"error": "Código no válido."}), 400
        
        # Crear un nuevo Artista con los datos de Valido
        new_artist = Artista(correo=valid_user.correo, nombreUsuario=valid_user.nombreUsuario,
                             contrasenya=valid_user.contrasenya, fotoPerfil="DEFAULT",
                             volumen=50, nombreArtistico=valid_user.nombreArtistico, 
                             biografia=None, tokenVersion=valid_user.tokenVersion)  # Se puede dejar vacía por ahora

        # Eliminar el usuario de Valido
        db.delete(valid_user)
        db.flush()
        db.add(new_artist)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        artista_dict=new_artist.to_dict()
    access_token = create_access_token(identity=new_artist.correo,
                                       additional_claims={"tokenVersion": new_artist.tokenVersion,
                                                          "tipo": "artista"},
                                       expires_delta=timedelta(hours=1))
    return jsonify({"token": access_token, "artista_valido": artista_dict}), 200


"""Envia un correo con un codigo para restablecer la contraseña en caso de olvido"""
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    correo = data.get("correo")
    if not correo:
        return jsonify({"error": "Faltan campos en la peticion."}), 400   

    with get_db() as db:
        # Comprobar que usario existe
        usuario = db.get(Usuario, correo)
        if not usuario:
            return jsonify({"error": "Correo no válido."}), 400

        # Generar codigo numerico aleatorio de 6 digitos
        codigo = new_code()
        codigoHash = hash(codigo)

        # Crear nueva entrada en la tabla ContraReset
        reset_entry = ContraReset(Usuario_correo=correo, codigo=codigoHash)
        db.add(reset_entry)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    # Enviar correo con el codigo
    send_mail(correo, "Recuperacion de contraseña",
              f"Tu código de recuperación de contraseña es: {codigo}. Vuelve a la aplicación e introdúcelo.")

    return jsonify({"okay": "Todo ha ido bien."}), 200


"""Verifica la validez del codigo para restablecer la contraseña en caso de olvido"""
@auth_bp.route('/verify-codigo', methods=['POST'])
def verify_codigo():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    correo = data.get("correo")
    codigo = data.get("codigo")
    if not correo or not codigo:
        return jsonify({"error": "Faltan datos en la petición."}), 400

    with get_db() as db:
        # Comprobar que existe codigo
        reset_entry = db.get(ContraReset, correo)
        if not reset_entry:
            return jsonify({"error": "Correo no existe."}), 400
        
        # Comprobar codigo correcto
        if not verify(codigo, reset_entry.codigo):
            return jsonify({"error": "Código no válido."}), 400
        
        # Eliminar codigo usado
        db.delete(reset_entry)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
        # Token temporal para cambiar contraseña
        token = create_access_token(identity=correo, expires_delta=timedelta(minutes=5),
                                    additional_claims={"reset-password": "yes"})
    return jsonify({"token_temporal": token}), 200


"""Restablece la contraseña en caso de olvido"""
@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    claims = get_jwt()
    if not claims.get("reset-password"):
        return jsonify({"error": "Token de cambio de contraseña no valido."}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    # Recuperar campos peticion
    correo = get_jwt_identity()
    nueva_contrasenya = data.get("nueva_contrasenya")
    if not correo or not nueva_contrasenya:
        return jsonify({"error": "Faltan datos"}), 400
    
    with get_db() as db:
        # Comprobar usuario existe
        usuario = db.get(Usuario, correo)
        if not usuario:
            return jsonify({"error": "Correo no existe."}), 400

        # Actualizar contraseña con hash seguro
        usuario.contrasenya = hash(nueva_contrasenya)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    return jsonify({"message": "Contraseña cambiada con éxito."}), 200


"""Elimina una cuenta de la app"""
@auth_bp.route('/delete-account', methods=['POST'])
@jwt_required()
@tokenVersion_required()
def delete_account():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    contrasenya = data.get("contrasenya")
    if not correo:
        return jsonify({"error": "Faltan campos en la peticion."}), 400  

    correo = get_jwt_identity()
    with get_db() as db:
        usuario = db.get(correo)
        if not verify(contrasenya, usuario.contrasenya):
            return jsonify({"error": "Contraseña incorrecta."}), 401

        db.delete(usuario)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
    return jsonify({"message": "Cuenta eliminada con éxito."}), 200


"""Cierra sesion en la app"""
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@tokenVersion_required()
def logout():
    correo = get_jwt_identity()
    with get_db() as db:
        # Invalidar token
        usuario = db.get(Usuario, correo)
        usuario.tokenVersion += 1
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    return jsonify({"message": "Sesion cerrada con éxito."}), 200
