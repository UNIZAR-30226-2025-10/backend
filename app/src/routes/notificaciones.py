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

        return jsonify({"notificaciones": any([notif_cancion, notif_album, invitado_playlist, like_no_visto, noizzito_no_visto])}), 200


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
