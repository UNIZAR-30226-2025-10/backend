from datetime import datetime
import pytz
from utils.decorators import roles_required, tokenVersion_required
from db.models import Noizzy, Noizzito, Like, Cancion, Album, notificacionCancion_table, notificacionAlbum_table, invitado_table, Oyente, sigue_table
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, jsonify
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import select, and_, exists, delete

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
        # Hay NotificacionCancion?
        notif_cancion = db.query(
            exists().where(notificacionCancion_table.c.Oyente_correo == correo)
        ).scalar()

        # Hay NotificacionAlbum?
        notif_album = db.query(
            exists().where(notificacionAlbum_table.c.Oyente_correo == correo)
        ).scalar()

        # Hay invitaciones a playlist?
        invitado_playlist = db.query(
            exists().where(invitado_table.c.Oyente_correo == correo)
        ).scalar()

        # Hay Like no visto?
        like_no_visto = db.query(
            exists().where(
                (Like.Oyente_correo == correo) &
                (Like.visto == False)
            )
        ).scalar()

        # Hay Noizzito no visto cuyo Noizzy pertenece al oyente?
        noizzito_no_visto = db.query(
            exists().where(
                (Noizzito.visto == False) &
                (Noizzito.Noizzy_id == Noizzy.id) &
                (Noizzy.Oyente_correo == correo)
            )
        ).scalar()

        return jsonify({"invitaciones": invitado_playlist,
                        "novedades-musicales": notif_album or notif_cancion,
                        "interacciones": like_no_visto or noizzito_no_visto,
                        "seguidores": False}), 200


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
    correo = get_jwt_identity()
    with get_db() as db:
        NoizzyAlias = aliased(Noizzy)
        stmt = select(Noizzito
                ).join(NoizzyAlias, Noizzito.Noizzy_id == NoizzyAlias.id
                ).where(and_(NoizzyAlias.Oyente_correo == correo,
                    Noizzito.visto == False))
        
        respuestas = db.execute(stmt).scalars().all()
        
        stmt = select(Like
                ).join(Noizzy, Noizzy.id == Like.Noizzy_id
                ).where(and_(Noizzy.Oyente_correo == correo,
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


"""Elimina todas las notificaciones de novedades musicales del usuario logueado"""
@notificacion_bp.route("/delete-novedades-musicales", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def delete_novedades_musicales():    
    correo = get_jwt_identity()
    with get_db() as db:
        stmt_canciones = delete(notificacionCancion_table).where(notificacionCancion_table.c.Oyente_correo == correo)
        stmt_albumes = delete(notificacionAlbum_table).where(notificacionAlbum_table.c.Oyente_correo == correo)

        result_canciones = db.execute(stmt_canciones)
        result_albumes = db.execute(stmt_albumes)
        if result_canciones.rowcount == 0 and result_albumes.rowcount == 0:
            return jsonify({"error": "No existen notificaciones de novedades musicales."}), 404
        
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
                    "noizzy": respuestas[i].id,
                    "texto": respuestas[i].texto,
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
                    "noizzy": l.id,
                    "texto": l.texto,
                    "tipo": "like"
                })

        return jsonify(resultado), 200

