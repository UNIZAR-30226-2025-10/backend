from utils.decorators import roles_required, tokenVersion_required
from db.models import Noizzy, Noizzito, Like, Cancion, Album, notificacionCancion_table, notificacionAlbum_table, invitado_table, Oyente, Sigue
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import select, and_, exists, delete, desc

notificacion_bp = Blueprint('notificacion', __name__) 

"""Devuelve True si hay notificaciones (invitaciones a playlists, noizzitos, likes, 
   nuevas canciones o albumes) para el usuario logueado"""
@notificacion_bp.route("/has-notificaciones", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def has_notificaciones():
    correo = get_jwt_identity()

    with get_db() as db:
        # Notificación de canción
        notif_cancion = db.execute(
            select(exists().where(notificacionCancion_table.c.Oyente_correo == correo))
        ).scalar()

        # Notificación de álbum
        notif_album = db.execute(
            select(exists().where(notificacionAlbum_table.c.Oyente_correo == correo))
        ).scalar()

        # Invitaciones a playlist
        invitado_playlist = db.execute(
            select(exists().where(invitado_table.c.Oyente_correo == correo))
        ).scalar()

        # Likes no vistos
        like_no_visto = db.execute(
            select(exists().where(
                (Like.visto == False) &
                (Like.Noizzy_id == Noizzy.id) &
                (Noizzy.Oyente_correo == correo)
            ))
        ).scalar()

        # Noizzitos no vistos cuyo Noizzy pertenece al oyente
        noizzito_no_visto = db.execute(
            select(exists().where(
                (Noizzito.visto == False) &
                (Noizzito.Noizzy_id == Noizzy.id) &
                (Noizzy.Oyente_correo == correo)
            ))
        ).scalar()

        # Nuevos seguidores no vistos
        seguidor_no_visto = db.execute(
            select(exists().where(
                (Sigue.visto == False) &
                (Sigue.Seguido_correo == correo)
            ))
        ).scalar()

        return jsonify({"invitaciones": invitado_playlist,
                        "novedades-musicales": notif_album or notif_cancion,
                        "interacciones": like_no_visto or noizzito_no_visto,
                        "seguidores": seguidor_no_visto}), 200


"""Devuelve una lista con las notificaciones de novedades musicales """
@notificacion_bp.route("/get-novedades-musicales", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_novedades_musicales():
    correo = get_jwt_identity()
    with get_db() as db:
        stmt_canciones = select(Cancion
                       ).join(notificacionCancion_table, notificacionCancion_table.c.Cancion_id == Cancion.id
                       ).where(notificacionCancion_table.c.Oyente_correo == correo
                       ).options(
                           selectinload(Cancion.artista),
                           selectinload(Cancion.album),
                           selectinload(Cancion.featuring)
                       ).order_by(Cancion.fecha.desc())
        
        stmt_albumes = select(Album
                       ).join(notificacionAlbum_table, notificacionAlbum_table.c.Album_id == Album.id
                       ).where(notificacionAlbum_table.c.Oyente_correo == correo
                       ).options(selectinload(Album.artista)
                       ).order_by(Album.fecha.desc())
        
        canciones = db.execute(stmt_canciones).scalars().all()
        albumes = db.execute(stmt_albumes).scalars().all()

        # Función para extraer la información de Cancion
        def format_cancion(cancion):
            return {"id": cancion.id,
                    "nombre": cancion.nombre,
                    "tipo": "cancion",
                    "fotoPortada": cancion.album.fotoPortada,
                    "nombreArtisticoArtista": cancion.artista.nombreArtistico,
                    "featuring": [f.nombreArtistico for f in cancion.featuring]}

        # Función para extraer la información de Album
        def format_album(album):
            return {"id": album.id,
                    "nombre": album.nombre,
                    "tipo": "album",
                    "fotoPortada": album.fotoPortada,
                    "nombreArtisticoArtista": album.artista.nombreArtistico,
                    "featuring": []}
        
        resultado = []
        i, j = 0, 0
        while i < len(canciones) and j < len(albumes):
            if canciones[i].fecha > albumes[j].fecha:
                resultado.append(format_cancion(canciones[i]))
                i += 1
            else:
                resultado.append(format_album(albumes[j]))
                j += 1

        resultado.extend(format_cancion(c) for c in canciones[i:])
        resultado.extend(format_album(a) for a in albumes[j:])

        return jsonify({"resultado": resultado}), 200


"""Marca todas notificaciones de interacciones con un noizzy del usuario logueado como leidas"""
@notificacion_bp.route("/read-interacciones", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def read_interacciones():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400
    
    noizzy_id = data.get("noizzy")
    if not noizzy_id:
        return jsonify({"error": "Falta el id del noizzy."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        noizzy = db.get(Noizzy, noizzy_id)
        if not noizzy:
            return jsonify({"error": "No existe el noizzy."}), 404
        
        if noizzy.Oyente_correo != correo:
            return jsonify({"error": "No tienes permiso para eliminar notificaciones de este noizzy."}), 403
        
        stmt = select(Noizzito
                ).where(and_(Noizzito.Noizzy_id == noizzy_id,
                    Noizzito.visto == False))
        
        respuestas = db.execute(stmt).scalars().all()
        
        stmt = select(Like
                ).where(and_(Like.Noizzy_id == noizzy_id,
                    Like.visto == False))
        
        likes = db.execute(stmt).scalars().all()
        
        if not likes and not respuestas:
            return jsonify({"error": "No existen notificaciones de interacciones."}), 404

        for respuesta in respuestas:
            respuesta.visto = True

        for like in likes:
            like.visto = True

        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 200


"""Elimina una notificacion de nueva cancion"""
@notificacion_bp.route("/delete-notificacion-cancion", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def delete_notificacion_cancion():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400
    
    cancion_id = data.get("cancion")
    if not cancion_id:
        return jsonify({"error": "Faltan el id de la cancion de la notificacion."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        stmt = delete(notificacionCancion_table).where(and_(
            (notificacionCancion_table.c.Oyente_correo == correo),
            (notificacionCancion_table.c.Cancion_id == cancion_id)))

        result = db.execute(stmt)
        if result.rowcount == 0:
            return jsonify({"error": "No existe la notificacion."}), 404
        
        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204


"""Elimina una notificacion de nuevo album"""
@notificacion_bp.route("/delete-notificacion-album", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def delete_notificacion_album():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400
    
    album_id = data.get("album")
    if not album_id:
        return jsonify({"error": "Faltan el id de la album de la notificacion."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        stmt = delete(notificacionAlbum_table).where(and_(
            (notificacionAlbum_table.c.Oyente_correo == correo),
            (notificacionAlbum_table.c.Album_id == album_id)))

        result = db.execute(stmt)
        if result.rowcount == 0:
            return jsonify({"error": "No existe la notificacion."}), 404
        
        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204


"""Devuelve una lista con las notificaciones de noizzito"""
@notificacion_bp.route("/get-interacciones", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_interacciones():
    correo = get_jwt_identity()
    with get_db() as db:
        NoizzyAlias = aliased(Noizzy)
        stmt = select(Noizzito
                ).join(NoizzyAlias, Noizzito.Noizzy_id == NoizzyAlias.id
                ).where(and_(NoizzyAlias.Oyente_correo == correo,
                    Noizzito.visto == False)
                ).options(
                    selectinload(Noizzito.oyente)
                ).order_by(Noizzito.fecha.desc())
        
        respuestas = db.execute(stmt).scalars().all()
        
        stmt = select(Like
                ).join(Noizzy, Noizzy.id == Like.Noizzy_id
                ).where(and_(Noizzy.Oyente_correo == correo,
                    Like.visto == False)
                ).options(
                    selectinload(Like.oyente),
                    selectinload(Like.noizzy)    
                ).order_by(Like.fecha.desc())
        
        likes = db.execute(stmt).scalars().all()
        
        resultado = []
        i, j = 0, 0
        while i < len(respuestas) and j < len(likes):
            if respuestas[i].fecha > likes[j].fecha:
                resultado.append({
                    "nombreUsuario": respuestas[i].oyente.nombreUsuario,
                    "noizzy": respuestas[i].noizzy.id,
                    "texto": respuestas[i].noizzy.texto,
                    "tipo": "respuesta"
                })
                i += 1
            else:
                resultado.append({
                    "nombreUsuario": likes[j].oyente.nombreUsuario,
                    "noizzy": likes[j].noizzy.id,
                    "texto": likes[j].noizzy.texto,
                    "tipo": "like"
                })
                j += 1

        for r in respuestas[i:]:
            resultado.append({
                    "nombreUsuario": r.oyente.nombreUsuario,
                    "noizzy": r.noizzy.id,
                    "texto": r.noizzy.texto,
                    "tipo": "respuesta"
                })

        for l in likes[j:]:
            resultado.append({
                    "nombreUsuario": l.oyente.nombreUsuario,
                    "noizzy": l.noizzy.id,
                    "texto": l.noizzy.texto,
                    "tipo": "like"
                })

        return jsonify(resultado), 200


"""Marca una notificaciones de nuevo seguidor del usuario logueado como leida"""
@notificacion_bp.route("/read-nuevo-seguidor", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def read_nuevo_seguidor():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan campos en la petición."}), 400
    
    nombreUsuario = data.get("nombreUsuario")
    if not nombreUsuario:
        return jsonify({"error": "Falta el nombre del usuario."}), 400
    
    correo = get_jwt_identity()
    with get_db() as db:
        oyente = db.execute(select(Oyente).filter_by(nombreUsuario=nombreUsuario)).scalar_one_or_none()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404

        sigue = db.execute(select(Sigue).where(and_(Sigue.Seguidor_correo == oyente.correo, Sigue.Seguido_correo == correo, Sigue.visto == False))).scalar_one_or_none()
        if not sigue:
            return jsonify({"error": "No existe la notificación."}), 404
        
        sigue.visto = True

        try:
            db.commit() 
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204 


"""Devuelve una lista con las notificaciones de nuevos seguidores"""
@notificacion_bp.route("/get-nuevos-seguidores", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_nuevos_seguidores():
    correo = get_jwt_identity()
    with get_db() as db:
        stmt = select(Oyente
                       ).join(Sigue, Sigue.Seguidor_correo == Oyente.correo
                       ).where(and_(Sigue.Seguido_correo == correo, Sigue.visto == False)
                       ).order_by(desc(Sigue.fecha))
        
        seguidores = db.execute(stmt).scalars().all()
        seguidores_dict = [{
            "nombre": s.nombreUsuario if s.tipo == "oyente" else s.nombreArtistico,
            "nombreUsuario": s.nombreUsuario,
            "fotoPerfil": s.fotoPerfil,
            "tipo": s.tipo
        } for s in seguidores]

        return jsonify({"resultado": seguidores_dict}), 200