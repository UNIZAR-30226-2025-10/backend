from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from db.db import get_db
from db.models import *
from utils.hash import hash
from utils.code import new_code
from utils.mail import send_mail
from utils.decorators import roles_required, tokenVersion_required

admin_bp = Blueprint('admin', __name__) 

"""Devuelve una lista con todos los usuarios registrados como 
   artistas pendientes de validacion"""
@admin_bp.route('/get-pendientes', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("admin")
def get_pendientes():
    with get_db() as db:
        pendientes_result = db.execute(select(Pendiente)).scalars().all()
        pendientes = [{"correo": p.correo, "nombreArtistico": p.nombreArtistico} 
                      for p in pendientes_result]
    
    return jsonify({"pendientes": pendientes}), 200


"""Valida o invalida una cuenta de artista pendiente:
    - si es valida genera un codigo de verificacion y la cuenta de artista pasa 
      a ser valida
    - si no es valida elimina la cuenta de artista
   En ambos casos envia un correo al usuario notificando la decision"""
@admin_bp.route('/check-artista', methods=['POST'])
@jwt_required()
@tokenVersion_required()
@roles_required("admin")
def check_artista():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400

    # Recuperar campos peticion
    correo = data.get("correo")
    valido = data.get("valido")
    if not correo or valido is None:
        return jsonify({"error": "Faltan campos en la petición."}), 400  
    
    with get_db() as db:
        # Comprobar correo pendiente existe
        pendiente_entry = db.get(Pendiente, correo)
        if not pendiente_entry:
            return jsonify({"error": "Correo no existe."}), 401
        
        if valido:
            # Generar codigo numerico aleatorio de 6 digitos
            codigo = new_code()  
            codigoHash = hash(codigo)
            
            # Eliminar la entrada de Pendiente
            db.delete(pendiente_entry)
            db.flush()

            # Insertar como valido
            valido_entry = Valido(correo=pendiente_entry.correo, nombreUsuario=pendiente_entry.nombreUsuario,
                                  contrasenya=pendiente_entry.contrasenya, 
                                  nombreArtistico=pendiente_entry.nombreArtistico, codigo=codigoHash,
                                  tokenVersion=pendiente_entry.tokenVersion)
            db.add(valido_entry)

            mensaje = f"¡Enhorabuena! Has sido validado como artista en Noizz. Introduce el siguiente código en la app: {codigo}."
        
        else:
            # Eliminar usuario
            db.delete(pendiente_entry)

            mensaje = f"Lo sentimos, pero el equipo de Noizz no te ha validado como artista. ¡Vuelve a intentarlo en un futuro!"

        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
            
    # Enviar correo notificando decision
    send_mail(correo, "Registro de artista en Noizz", mensaje)
    return jsonify(""), 200