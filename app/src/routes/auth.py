from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from db.db import get_db
from db.models import *
from utils.hash import hash, verify
from utils.code import new_code
from utils.mail import send_mail
from utils.decorators import roles_required, tokenVersion_required
from datetime import timedelta, datetime
import pytz

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
        if usuario.sesionActiva:
            return jsonify({"error": "Ya hay una sesion iniciada."}), 403
        
        usuario.sesionActiva = True
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        usuario_dict = {
            "fotoPerfil": usuario.fotoPerfil,
            "volumen": usuario.volumen
        } if usuario.tipo in ["oyente", "artista"] else None
        tipo = usuario.tipo

    access_token = create_access_token(identity=usuario.correo, 
                                       additional_claims={"tokenVersion": usuario.tokenVersion,
                                                          "tipo": usuario.tipo},
                                       expires_delta=timedelta(hours=1))

    if usuario_dict:
        return jsonify({"token": access_token, "usuario": usuario_dict, "tipo": tipo}), 200
    else:
        return jsonify({"token": access_token, "tipo": tipo}), 200


"""Cierra sesion en la app y abre una nueva"""
@auth_bp.route("/switch-session", methods=["POST"])
def switch_session():
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
        if not usuario.sesionActiva:
            return jsonify({"error": "La sesion no ha sido iniciada."}), 403
        
        usuario.tokenVersion += 1
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        usuario_dict = {
            "fotoPerfil": usuario.fotoPerfil,
            "volumen": usuario.volumen
        } if usuario.tipo in ["oyente", "artista"] else None
        tipo = usuario.tipo

    access_token = create_access_token(identity=usuario.correo, 
                                       additional_claims={"tokenVersion": usuario.tokenVersion,
                                                          "tipo": usuario.tipo},
                                       expires_delta=False)

    if usuario_dict:
        return jsonify({"token": access_token, "usuario": usuario_dict, "tipo": tipo}), 200
    else:
        return jsonify({"token": access_token, "tipo": tipo}), 200
    

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
                            volumen=50, tokenVersion=1, sesionActiva=True)
        fav_playlist = Playlist(nombre="Favoritos", fotoPortada="DEFAULT", Oyente_correo=correo,
                                privacidad=False, fecha=datetime.now(pytz.timezone('Europe/Madrid')))
        db.add(oyente) 
        db.add(fav_playlist) 
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    access_token = create_access_token(identity=oyente.correo,
                                       additional_claims={"tokenVersion": 1,
                                                          "tipo": "oyente"},
                                       expires_delta=timedelta(hours=1))
    return jsonify({"token": access_token, 
                    "oyente": {"fotoPerfil": oyente.fotoPerfil,
                               "volumen": oyente.volumen}, 
                    "tipo": "oyente"}), 201 


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
            return jsonify({"error": f"El correo {correo_entry.correo} ya está en uso."}), 409
        # Comprobar nombreUsuario no existe
        nombreUsuario_entry = db.query(Usuario).filter(Usuario.nombreUsuario == nombreUsuario).first()
        if nombreUsuario_entry:
            return jsonify({"error": f"El nombre de usuario {nombreUsuario_entry.nombreUsuario} ya está en uso."}), 409

        # Insertar usuario pendiente de validacion
        contrasenyaHash = hash(contrasenya)           
        pendiente = Pendiente(correo=correo, nombreUsuario=nombreUsuario,
                              contrasenya=contrasenyaHash, nombreArtistico=nombreArtistico,
                              tokenVersion=1, sesionActiva=True)
        db.add(pendiente) 
        try:
            db.commit() 
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        access_token = create_access_token(identity=pendiente.correo,
                                       additional_claims={"tokenVersion": 1,
                                                          "tipo": "pendiente"},
                                       expires_delta=timedelta(hours=1))

    return jsonify({"token": access_token, "tipo": "pendiente"}), 201


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
                             biografia=None, tokenVersion=valid_user.tokenVersion, sesionActiva=True) 
        fav_playlist = Playlist(nombre="Favoritos", fotoPortada="DEFAULT", Oyente_correo=valid_user.correo,
                                privacidad=False, fecha=datetime.now(pytz.timezone('Europe/Madrid')))

        # Eliminar el usuario de Valido
        db.delete(valid_user)
        db.flush()
        db.add(new_artist)
        db.add(fav_playlist)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    access_token = create_access_token(identity=new_artist.correo,
                                       additional_claims={"tokenVersion": new_artist.tokenVersion,
                                                          "tipo": "artista"},
                                       expires_delta=timedelta(hours=1))
    return jsonify({"token": access_token, 
                    "artista_valido": {"fotoPerfil": new_artist.fotoPerfil,
                                       "volumen": new_artist.volumen}, 
                    "tipo": "artista"}), 201


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

        # Comprobar usuario no tiene codigo
        reset_entry = db.get(ContraReset, correo)
        if reset_entry:
            # Actualizar entrada en tabla ContraReset
            reset_entry.codigo=codigoHash
        else:
            # Crear nueva entrada en tabla ContraReset
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

    return jsonify(""), 200


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
    return jsonify({"token_temporal": token}), 201


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

    return jsonify(""), 201


"""Elimina una cuenta de la app"""
@auth_bp.route('/delete-account', methods=['DELETE'])
@jwt_required()
@tokenVersion_required()
def delete_account():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    contrasenya = data.get("contrasenya")
    if not contrasenya:
        return jsonify({"error": "Faltan campos en la peticion."}), 400  

    correo = get_jwt_identity()
    with get_db() as db:
        usuario = db.get(Usuario, correo)
        if not verify(contrasenya, usuario.contrasenya):
            return jsonify({"error": "Contraseña incorrecta."}), 401

        db.delete(usuario)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
    return jsonify(""), 204


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
        usuario.sesionActiva = False
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    return jsonify(""), 200
