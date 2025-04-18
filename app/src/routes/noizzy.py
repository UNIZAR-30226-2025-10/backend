from datetime import datetime
import pytz
from utils.decorators import roles_required, tokenVersion_required
from db.models import Noizzy, Noizzito, Like, Artista, Coleccion, Cancion, Oyente, sin_leer_table, Sigue, Usuario
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify
from sqlalchemy import select, and_, func, delete, insert, exists, literal, desc, case
from sqlalchemy.orm import selectinload, aliased
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
        oyente_actual = db.get(Oyente, correo)
        # Subquery para contar comentarios
        noizzito_table = Noizzito.__table__
        subquery_num_comentarios = select(func.count(noizzito_table.c.Noizzy_id)).where(noizzito_table.c.Noizzy_id == Noizzy.id).scalar_subquery()

        # Subquery para contar likes totales
        subquery_num_likes = select(func.count(Like.Noizzy_id)).where(Like.Noizzy_id == Noizzy.id).scalar_subquery()
        
        # Subquery para verificar si el usuario dio like
        subquery_user_like = select(func.count(Like.Noizzy_id)).where((Like.Noizzy_id == Noizzy.id) & (Like.Oyente_correo == correo)).scalar_subquery()

        # Consulta principal
        oyente_publicador = aliased(Oyente)
        usuario_publicador = aliased(Usuario)
        artista_publicador = aliased(Artista)  # artista que publicó el Noizzy, si lo es
        artista_cancion = aliased(Artista)     # artista de la canción
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                subquery_num_likes.label("num_likes"),
                subquery_num_comentarios.label("num_comentarios"),
                subquery_user_like.label("user_like_exists"),
                artista_cancion.nombreArtistico, Coleccion.fotoPortada, oyente_publicador.nombreUsuario,
                oyente_publicador.fotoPerfil, Cancion.nombre, artista_publicador.nombreArtistico
            ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
            ).outerjoin(artista_cancion, artista_cancion.correo == Cancion.Artista_correo
            ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
            ).outerjoin(oyente_publicador, oyente_publicador.correo == Noizzy.Oyente_correo
            ).outerjoin(usuario_publicador, usuario_publicador.correo == oyente_publicador.correo
            ).outerjoin(artista_publicador, artista_publicador.correo == oyente_publicador.correo
            ).where(Noizzy.id == id)

        noizzy = db.execute(stmt).first()
        if not noizzy or not noizzy[0]:
            return jsonify({"error": "Noizzy no encontrado."}), 404
        
        result = {
            "fotoPerfil": noizzy[10],
            "nombreUsuario": noizzy[9] if not noizzy[12] else noizzy[12],
            "mio": noizzy[9] == oyente_actual.nombreUsuario,
            "fecha": noizzy[1].strftime("%d %m %Y %H %M"),
            "texto": noizzy[2],
            "num_likes": noizzy[4],
            "num_comentarios": noizzy[5],
            "like": True if noizzy[6] else False,
            "cancion": {
                "id": noizzy[3],
                "nombre": noizzy[11],
                "nombreArtisticoArtista": noizzy[7],
                "fotoPortada": noizzy[8]
            } if noizzy[3] else None
        }       

        subquery_num_comentarios = select(func.count(noizzito_table.c.Noizzy_id)).where(noizzito_table.c.Noizzy_id == Noizzy.id).correlate(Noizzy).scalar_subquery()
        stmt_noizzitos = select(Noizzito.id, Noizzito.fecha, Noizzito.texto, Noizzito.Cancion_id,
                subquery_num_likes.label("num_likes"),
                subquery_num_comentarios.label("num_comentarios"),
                subquery_user_like.label("user_like_exists"),
                artista_cancion.nombreArtistico, Coleccion.fotoPortada, oyente_publicador.nombreUsuario,
                oyente_publicador.fotoPerfil, Cancion.nombre, artista_publicador.nombreArtistico
            ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
            ).outerjoin(artista_cancion, artista_cancion.correo == Cancion.Artista_correo
            ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
            ).outerjoin(oyente_publicador, oyente_publicador.correo == Noizzy.Oyente_correo
            ).outerjoin(usuario_publicador, usuario_publicador.correo == oyente_publicador.correo
            ).outerjoin(artista_publicador, artista_publicador.correo == oyente_publicador.correo
            ).where(Noizzito.Noizzy_id == id
            ).order_by(Noizzito.fecha.desc())
        
        noizzitos_result = db.execute(stmt_noizzitos).all()
        
        noizzitos = [
            {
                "nombreUsuario": row[9] if not row[12] else row[12],
                "mio": row[9] == oyente_actual.nombreUsuario,
                "fotoPerfil": row[10],
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[6] else False,
                "cancion": {
                    "id": row[3],
                    "fotoPortada": row[8],
                    "nombreArtisticoArtista": row[7],
                    "nombre": row[11]
                } if row[3] else None,
                "num_likes": row[4],
                "num_comentarios": row[5]
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
        noizzy_entry = db.get(Noizzy, noizzy)
        if not noizzy_entry:
            return jsonify({"error": "No existe el noizzy."}), 404 
        
        if not cancion:
            new_entry = Noizzito(Oyente_correo=correo, Noizzy_id=noizzy, tipo="noizzito", fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                             texto=texto, visto=(noizzy_entry.Oyente_correo == correo), Cancion_id=None)
        else:
            new_entry = Noizzito(Oyente_correo=correo, Noizzy_id=noizzy, tipo="noizzito", fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                             texto=texto, visto=(noizzy_entry.Oyente_correo == correo), Cancion_id=cancion)
        
        usuario = db.get(Oyente, correo)

        db.add(new_entry)
        try:
            db.commit()       
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
        # Websockets para notificacion en tiempo real
        if correo != noizzy_entry.Oyente_correo:
            socketio.emit("nueva-interaccion-ws", {"nombreUsuario": new_entry.oyente.nombreUsuario,
                                                   "fotoPerfil": new_entry.oyente.fotoPerfil,
                                                    "noizzy": noizzy,
                                                    "noizzito": new_entry.id,
                                                    "texto": noizzy_entry.texto,
                                                    "tipo": "respuesta"}
                                                , room=new_entry.noizzy.oyente.correo)
            
        stmt = (select(Oyente.correo)
                .where(Oyente.sesionActiva == True))

        activos = db.execute(stmt).scalars().all()    
        
        for activo in activos:
            socketio.emit("actualizar-noizzito-ws", {"nombreUsuario": usuario.nombreUsuario if usuario.tipo == "oyente" else usuario.nombreArtistico,
                "fotoPerfil": usuario.fotoPerfil,
                "id": new_entry.id,
                "texto": new_entry.texto,
                "fecha": new_entry.fecha.strftime("%d %m %y %H %M"),
                "cancion": {
                    "id": new_entry.cancion.id,
                    "nombre": new_entry.cancion.nombre,
                    "fotoPortada": new_entry.cancion.album.fotoPortada,
                    "nombreArtisticoArtista": new_entry.cancion.artista.nombreArtistico
                } if new_entry.cancion else None}, room=activo) 
    
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

        # Subquery para contar comentarios
        noizzito_table = Noizzito.__table__
        subquery_num_comentarios = select(func.count(noizzito_table.c.Noizzy_id)).where(noizzito_table.c.Noizzy_id == Noizzy.id).scalar_subquery()

        # Subquery para contar likes totales
        subquery_num_likes = select(func.count(Like.Noizzy_id)).where(Like.Noizzy_id == Noizzy.id).scalar_subquery()
        
        # Subquery para verificar si el usuario dio like
        subquery_user_like = select(func.count(Like.Noizzy_id)).where((Like.Noizzy_id == Noizzy.id) & (Like.Oyente_correo == correo)).scalar_subquery()
        
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                subquery_num_likes.label("num_likes"),
                subquery_num_comentarios.label("num_comentarios"),
                subquery_user_like.label("user_like_exists"),
                Artista.nombreArtistico, Coleccion.fotoPortada, Cancion.nombre,
            ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
            ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
            ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
            ).where(and_(Noizzy.tipo == 'noizzy', Noizzy.Oyente_correo == oyente.correo)
            ).order_by(Noizzy.fecha.desc())

        noizzys = db.execute(stmt).all()
        noizzys_dict = [
            {
                "nombreUsuario": nombreUsuario if oyente.tipo == "oyente" else oyente.nombreArtistico,
                "fotoPerfil": oyente.fotoPerfil,
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[6] else False,
                "cancion": {
                    "id": row[3],
                    "nombre": row[9],
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
        
        # Subquery para contar comentarios
        noizzito_table = Noizzito.__table__
        subquery_num_comentarios = select(func.count(noizzito_table.c.Noizzy_id)).where(noizzito_table.c.Noizzy_id == Noizzy.id).scalar_subquery()

        # Subquery para contar likes totales
        subquery_num_likes = select(func.count(Like.Noizzy_id)).where(Like.Noizzy_id == Noizzy.id).scalar_subquery()
        
        # Subquery para verificar si el usuario dio like
        subquery_user_like = select(func.count(Like.Noizzy_id)).where((Like.Noizzy_id == Noizzy.id) & (Like.Oyente_correo == correo)).scalar_subquery()

        # Consulta principal
        stmt = select(Noizzy.id, Noizzy.fecha, Noizzy.texto, Noizzy.Cancion_id,
                subquery_num_likes.label("num_likes"),
                subquery_num_comentarios.label("num_comentarios"),
                subquery_user_like.label("user_like_exists"),
                Artista.nombreArtistico, Coleccion.fotoPortada, Cancion.nombre,
            ).outerjoin(Cancion, Cancion.id == Noizzy.Cancion_id
            ).outerjoin(Artista, Artista.correo == Cancion.Artista_correo
            ).outerjoin(Coleccion, Coleccion.id == Cancion.Album_id
            ).where(and_(Noizzy.tipo == 'noizzy', Noizzy.Oyente_correo == correo)
            ).order_by(Noizzy.fecha.desc())

        noizzys = db.execute(stmt).all()
        noizzys_dict = [
            {
                "nombreUsuario": usuario_entry.nombreUsuario if usuario_entry.tipo == "oyente" else usuario_entry.nombreArtistico,
                "fotoPerfil": usuario_entry.fotoPerfil,
                "fecha": row[1].strftime("%d %m %y %H %M"),
                "id": row[0],
                "texto": row[2],
                "like": True if row[6] else False,
                "cancion": {
                    "id": row[3],
                    "nombre": row[9],
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
        db.flush()

        seguidores_entry = db.get(Oyente, correo, options=[selectinload(Oyente.seguidores)])

        notificaciones = [
            {"Oyente_correo": seguidor.Seguidor_correo, "Noizzy_id": noizzy.id}
            for seguidor in seguidores_entry.seguidores
        ]

        if notificaciones:
            db.execute(insert(sin_leer_table), notificaciones)

        usuario = db.get(Oyente, correo)

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
        stmt = (select(Oyente.correo)
            .join(Sigue, Oyente.correo == Sigue.Seguidor_correo)
            .where(and_(Sigue.Seguido_correo == correo, Oyente.sesionActiva == True)))

        seguidores_oyentes = db.execute(stmt).scalars().all()

        for seguidor in seguidores_oyentes:
            # Emitir el evento de socket con la notificacion
            socketio.emit("new-noizzy-ws", {"nombreUsuario": usuario.nombreUsuario if usuario.tipo == "oyente" else usuario.nombreArtistico,
                                            "fotoPerfil": usuario.fotoPerfil,
                                            "tipo": usuario.tipo}, room=seguidor)

        stmt = (select(Oyente.correo)
                .where(Oyente.sesionActiva == True))

        activos = db.execute(stmt).scalars().all()    
        
        for activo in activos:
            socketio.emit("actualizar-noizzy-ws", {"nombreUsuario": usuario.nombreUsuario if usuario.tipo == "oyente" else usuario.nombreArtistico,
                "fotoPerfil": usuario.fotoPerfil,
                "id": noizzy.id,
                "texto": noizzy.texto,
                "fecha": noizzy.fecha.strftime("%d %m %y %H %M"),
                "cancion": {
                    "id": noizzy.cancion.id,
                    "nombre": noizzy.cancion.nombre,
                    "fotoPortada": noizzy.cancion.album.fotoPortada,
                    "nombreArtisticoArtista": noizzy.cancion.artista.nombreArtistico
                } if noizzy.cancion else None}, room=activo)  

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
            like_entry = Like(Oyente_correo=correo, Noizzy_id=noizzy, visto=(noizzy_entry.Oyente_correo == correo), fecha=datetime.now(pytz.timezone('Europe/Madrid')))
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
        
        # Websockets para notificacion en tiempo real
        if like and correo != noizzy_entry.Oyente_correo:
            socketio.emit("nueva-interaccion-ws", {"nombreUsuario": like_entry.oyente.nombreUsuario,
                                                   "fotoPerfil": like_entry.oyente.fotoPerfil,
                                                    "noizzy": like_entry.noizzy.id,
                                                    "noizzito": None,
                                                    "texto": like_entry.noizzy.texto,
                                                    "tipo": "like"}, room=like_entry.noizzy.oyente.correo)
        
    return jsonify(""), 200


"""Lee los noizzys de un perfil que estaban sin leer"""
@noizzy_bp.route("/read-noizzys", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def read_noizzys():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400
    
    oyente_nombreUsuario = data.get("nombreUsuario")
    if not oyente_nombreUsuario:
        return jsonify({"error": "Falta el nombre del usuario."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        oyente_entry = db.execute(select(Oyente).where(Oyente.nombreUsuario == oyente_nombreUsuario)).scalar_one_or_none()
        if not oyente_entry:
            return jsonify({"error": "No existe el usuario."}), 404
        
        stmt = delete(sin_leer_table).where(
            (sin_leer_table.c.Oyente_correo == correo) &
            (sin_leer_table.c.Noizzy_id.in_(
                select(Noizzy.id).where(Noizzy.Oyente_correo == oyente_entry.correo)))
        )

        result = db.execute(stmt)
        if result.rowcount == 0:
            return jsonify({"error": "No hay noizzys sin leer."}), 404
        
        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204


"""Devuelve una lista con los seguidos del usuario logueado en orden de actividad
   y si tienen noizzys sin leer"""
@noizzy_bp.route("/get-actividad-seguidos", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_actividad_seguidos():
    correo = get_jwt_identity()  

    with get_db() as db:
        sin_leer_subq = select(literal(1)
            ).where(and_(sin_leer_table.c.Oyente_correo == correo,
                         sin_leer_table.c.Noizzy_id.in_(
                            select(Noizzy.id).where(Noizzy.Oyente_correo == Usuario.correo).correlate(Usuario))))

        ultimo_noizzy_subq = select(Noizzy.fecha).where(
            Noizzy.Oyente_correo == Usuario.correo
        ).order_by(Noizzy.fecha.desc()).limit(1).correlate(Usuario)

        # Recuperar seguidos, si tienen noizzy sin leer y ordenados por fecha del ultimo noizzy
        stmt = select(Oyente, 
                      exists(sin_leer_subq).label("sin_leer"),
                      ultimo_noizzy_subq.label("ultimo_noizzy_fecha")
            ).join(Sigue, Sigue.Seguido_correo == Oyente.correo
            ).where(Sigue.Seguidor_correo == correo
            ).order_by(case((exists(sin_leer_subq), 1), else_=2),
                       desc("ultimo_noizzy_fecha"), desc(Sigue.fecha) 
            ).limit(30)
        
        seguidos = db.execute(stmt)
        seguidos_dict = [
            {
                "nombreUsuario": row[0].nombreUsuario,
                "fotoPerfil": row[0].fotoPerfil,
                "tipo": row[0].tipo,
                "sinLeer": row[1]
            }
            for row in seguidos
        ]

    return jsonify({"seguidos": seguidos_dict}), 200
