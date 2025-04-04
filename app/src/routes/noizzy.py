from datetime import datetime
import pytz
from utils.decorators import roles_required, tokenVersion_required
from db.models import Noizzy, Noizzito, Like, Artista, Coleccion, Cancion, Oyente
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify
from sqlalchemy import select, and_, func
from .websocket import socketio

noizzy_bp = Blueprint('noizzy', __name__) 

"""Devuelve informacion de un noizzy"""
@noizzy_bp.route("/get-datos-noizzy", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_datos_noizzy():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del noizzy."}), 400
    
    correo = get_jwt_identity()
    
    with get_db() as db:
        subquery_num_comentarios = select(func.count(Noizzito.id)).where(Noizzito.Noizzy_id == Noizzy.id).scalar_subquery()
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                      func.count(Like.Noizzy_id).label("num_likes"),
                      subquery_num_comentarios.label("num_comentarios"),
                      func.count(Like.Noizzy_id).filter(Like.Oyente_correo == correo).label("user_like_exists"),
                      Artista.nombreArtistico, Coleccion.fotoPortada
                ).outerjoin(Like, Like.Noizzy_id == Noizzy.id
                ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
                ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
                ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
                ).where(Noizzy.id == id
                ).group_by(Noizzy.id, Cancion.id, Artista.nombreArtistico, Coleccion.fotoPortada)

        noizzy = db.execute(stmt).first()
        if noizzy:
            result = {
                "id": noizzy[0],
                "fecha": noizzy[1].strftime("%d %m %Y %H %M"),
                "texto": noizzy[2],
                "num_likes": noizzy[4],
                "num_comentarios": noizzy[5],
                "like": True if noizzy[6] else False,
                "cancion": {
                    "id": noizzy[3],
                    "nombreArtisticoArtista": noizzy[7],
                    "fotoPortada": noizzy[8]
                } if noizzy[3] else None
            }
        else:
            return jsonify({"error": "Noizzy no encontrado."}), 404
        
        subquery_num_comentarios = (select(func.count(Noizzito.id)).where(Noizzito.Noizzy_id == Noizzito.id).scalar_subquery())

        stmt_noizzitos = select(
            Noizzito.id, Noizzito.fecha, Noizzito.texto,
            func.count(Like.Noizzy_id).label("num_likes"),
            subquery_num_comentarios.label("num_comentarios"),
            func.count(Like.Noizzy_id).filter(Like.Oyente_correo == correo).label("user_like_exists"),
            Noizzito.Cancion_id, Artista.nombreArtistico, Coleccion.fotoPortada, Oyente.nombreUsuario
        ).outerjoin(Like, Like.Noizzy_id == Noizzito.id
        ).outerjoin(Cancion, Cancion.id == Noizzito.Cancion_id
        ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
        ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
        ).outerjoin(Oyente, Oyente.correo == Noizzito.Oyente_correo
        ).where(Noizzito.Noizzy_id == id
        ).group_by(Noizzito.id, Cancion.id, Artista.nombreArtistico, Coleccion.fotoPortada
        ).order_by(Noizzito.fecha.desc())
        
        noizzitos_result = db.execute(stmt_noizzitos).all()
        
        noizzitos = [
            {
                "nombreUsuario": row[9],
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[5] else False,
                "cancion": {
                    "id": row[6],
                    "fotoPortada": row[8],
                    "nombreArtisticoArtista": row[7]
                } if row[6] else None,
                "num_likes": row[3],
                "num_comentarios": row[4]
            }
        for row in noizzitos_result]

    return jsonify({
        **result,
        "noizzitos": noizzitos
    }), 200


"""Añade un noizzito al usuario logueado"""
@noizzy_bp.route('/post-noizzito', methods=['POST'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def post_noizzito():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    texto = data.get("texto")
    noizzy = data.get("noizzy")
    cancion = data.get("cancion")

    if not texto or not noizzy:
        return jsonify({"error": "Faltan campos en la peticion."}), 400  

    correo = get_jwt_identity()
    with get_db() as db:
        if not cancion:
            new_entry = Noizzito(Oyente_correo=correo, Noizzy_id=noizzy, tipo="noizzito", fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                             texto=texto, visto=False, Cancion_id=None)
        else:
            new_entry = Noizzito(Oyente_correo=correo, Noizzy_id=noizzy, tipo="noizzito", fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                             texto=texto, visto=False, Cancion_id=cancion)
        db.add(new_entry)
        try:
            db.commit()
            db.refresh(new_entry)           
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 201


"""Elimina un noizzy del usuario logueado"""
@noizzy_bp.route('/delete-noizzy', methods=['DELETE'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def delete_noizzy():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos no válidos."}), 400

    # Recuperar campos peticion
    id = data.get("id")
    if not id:
        return jsonify({"error": "Faltan campos en la peticion."}), 400  

    correo = get_jwt_identity()
    with get_db() as db:
        noizzy = db.get(Noizzy, id)
        if not noizzy:
            return jsonify({"error": "El noizzy no existe."}), 404
        
        if correo != noizzy.Oyente_correo:
            return jsonify({"error": "El noizzy solo puede ser eliminado por su creador."}), 403

        db.delete(noizzy)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204

"""Devuelve los noizzys (no noizzitos) de un usuario"""
@noizzy_bp.route("/get-noizzys", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_noizzys():
    nombreUsuario = request.args.get("nombreUsuario")
    if not nombreUsuario:
        return jsonify({"error": "Falta el nombreUsuario del usuario."}), 400
    
    correo = get_jwt_identity()
    
    with get_db() as db:
        oyente = db.execute(select(Oyente).filter_by(nombreUsuario=nombreUsuario)).scalar_one_or_none()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404

        subquery_num_comentarios = select(func.count(Noizzito.id)).where(Noizzito.Noizzy_id == Noizzy.id).scalar_subquery()
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                      func.count(Like.Noizzy_id).label("num_likes"),
                      subquery_num_comentarios.label("num_comentarios"),
                      func.count(Like.Noizzy_id).filter(Like.Oyente_correo == correo).label("user_like_exists"),
                      Artista.nombreArtistico, Coleccion.fotoPortada
               ).outerjoin(Like, Like.Noizzy_id == Noizzy.id
               ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
               ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
               ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
               ).where(and_(Noizzy.tipo == 'noizzy', Noizzy.Oyente_correo == oyente.correo)
               ).group_by(Noizzy.id, Artista.nombreArtistico, Coleccion.fotoPortada
               ).order_by(Noizzy.fecha.desc())

        noizzys = db.execute(stmt).all()
        noizzys_dict = [
            {
                "nombreUsuario": nombreUsuario,
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[6] else False,
                "cancion": {
                    "id": row[3],
                    "fotoPortada": row[8],
                    "nombreArtisticoArtista": row[7]
                } if row[3] else None,
                "num_likes": row[4],
                "num_comentarios": row[5]
            }
        for row in noizzys]
    
    return jsonify({"noizzys": noizzys_dict}), 200


"""Devuelve los noizzys (no noizzitos) del usuario logueado"""
@noizzy_bp.route("/get-mis-noizzys", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_mis_noizzys():
    correo = get_jwt_identity()
    with get_db() as db:
        usuario_entry = db.get(Oyente, correo)

        subquery_num_comentarios = select(func.count(Noizzito.id)).where(Noizzito.Noizzy_id == Noizzy.id).scalar_subquery()
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                      func.count(Like.Noizzy_id).label("num_likes"),
                      subquery_num_comentarios.label("num_comentarios"),
                      func.count(Like.Noizzy_id).filter(Like.Oyente_correo == correo).label("user_like_exists"),
                      Artista.nombreArtistico, Coleccion.fotoPortada
               ).outerjoin(Like, Like.Noizzy_id == Noizzy.id
               ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
               ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
               ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
               ).where(and_(Noizzy.tipo == 'noizzy', Noizzy.Oyente_correo == correo)
               ).group_by(Noizzy.id, Artista.nombreArtistico, Coleccion.fotoPortada
               ).order_by(Noizzy.fecha.desc())

        noizzys = db.execute(stmt).all()
        noizzys_dict = [
            {
                "nombreUsuario": usuario_entry.nombreUsuario,
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[6] else False,
                "cancion": {
                    "id": row[3],
                    "fotoPortada": row[8],
                    "nombreArtisticoArtista": row[7]
                } if row[3] else None,
                "num_likes": row[4],
                "num_comentarios": row[5]
            }
        for row in noizzys]
    
    return jsonify({"noizzys": noizzys_dict}), 200


"""Añade un noizzy al usuario logueado y avisa a sus seguidores"""
@noizzy_bp.route("/post-noizzy", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def post_noizzy():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    texto = data.get('texto')
    cancion = data.get('cancion')
    if not texto:
        return jsonify({"error": "Falta el texto del noizzy."}), 400
    
    with get_db() as db:
        noizzy = Noizzy(Oyente_correo=correo, fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                        texto = texto, Cancion_id=cancion)
        db.add(noizzy)

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
        usuario_entry = db.get(Oyente, correo)

        for seguidor in usuario_entry.seguidores:
            # Emitir el evento de socket con la notificacion
            socketio.emit("new-noizzy-ws", {"nombreUsuario": usuario_entry.nombreUsuario,
                                            "fotoPerfil": usuario_entry.fotoPerfil,
                                            "tipo": usuario_entry.tipo}, room=seguidor.correo)
    
    return jsonify(""), 201
            
        
"""Actualiza el estado de like del usuario logueado a un noizzy"""
@noizzy_bp.route('/change-like', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def change_like():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    like = data.get("like")
    noizzy = data.get("noizzy")
    if noizzy is None or like is None:
        return jsonify({"error": "Faltan campos en la peticion."}), 400
    
    with get_db() as db:
        noizzy_entry = db.get(Noizzy, noizzy)
        if not noizzy_entry:
            return jsonify({"error": "El noizzy no existe."}), 404
        
        like_entry = db.get(Like, (correo, noizzy))    
        
        if like and not like_entry:
            # Si no le he dado like y like == True, darle like
            like_entry = Like(Oyente_correo=correo, Noizzy_id=noizzy, visto=False)
            db.add(like_entry)

        elif not like and like_entry:
            # Si le he dado like y like == False, quitarle el like
            db.delete(like_entry)

        elif like_entry:
            return jsonify({"error": "Ya has dado like a este noizzy."}), 409

        else:
            return jsonify({"error": "No has dado like a este noizzy."}), 404
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
    return jsonify(""), 200
