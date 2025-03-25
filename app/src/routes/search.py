from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, or_, case, and_, not_
from db.db import get_db
from db.models import Cancion, Playlist, Album, Artista, Oyente, sigue_table, invitado_table, participante_table, EsParteDePlaylist
from utils.decorators import roles_required, tokenVersion_required
import re

search_bp = Blueprint('search', __name__) 

LIMITE = 20

"""Devuelve 4 listas con las canciones, albumes, playlists y artistas
   que empiezan por el termino buscado"""
@search_bp.route("/search", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search():
    # Recuperar parametros peticion
    termino = request.args.get("termino").strip()
    termino_no_spaces = re.sub(r"\s+", "", termino)
    if not termino :
        return jsonify({
            "canciones": [],"albumes": [],
            "playlists": [], "artistas": [], "perfiles": []
        }), 200 

    with get_db() as db:
        # Buscar canciones
        stmt_canciones = select(Cancion 
            ).where(or_(
                Cancion.nombre.ilike(f"%{termino}%"),
                Cancion.album.ilike(f"%{termino}%")),  
            ).order_by(
                case((Cancion.nombre.ilike(f"{termino}%"), 1), else_=2),  
                case((Cancion.album.ilike(f"{termino}%"), 1), else_=2), 
                Cancion.reproducciones.desc()
            ).limit(LIMITE)

        stmt_albumes = select(Album
            ).where(Album.nombre.ilike(f"%{termino}%")
            ).order_by(
                case((Album.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Album.nombre.asc()
            ).limit(LIMITE)

        stmt_playlists = select(Playlist
            ).where(Playlist.nombre.ilike(f"%{termino}%")
            ).order_by(
                case((Playlist.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Playlist.nombre.asc()
            ).limit(LIMITE)
        
        stmt_artistas = select(Artista.nombreArtistico
            ).where(or_(
                Artista.nombreArtistico.ilike(f"%{termino}%"), 
                Artista.nombreUsuario.ilike(f"%{termino_no_spaces}%"))
            ).order_by(
                case((Artista.nombreArtistico.ilike(f"{termino}%"), 1),  
                (Artista.nombreUsuario.ilike(f"{termino_no_spaces}%"), 2), else_=3), 
                Artista.nombreArtistico.asc(), 
                Artista.nombreUsuario.asc()
            ).limit(LIMITE)
        
        stmt_perfiles = select(Oyente
            ).where(and_(
                Oyente.nombreUsuario.ilike(f"%{termino_no_spaces}%"), 
                not_(Oyente.tipo == "artista"))
            ).order_by(
                case((Oyente.nombreUsuario.ilike(f"{termino_no_spaces}%"), 1), else_=2), 
                Oyente.nombreUsuario.asc()
            ).limit(LIMITE)         

        canciones = db.execute(stmt_canciones).scalars().all()
        albumes = db.execute(stmt_albumes).scalars().all()
        playlists = db.execute(stmt_playlists).scalars().all()
        artistas = db.execute(stmt_artistas).scalars().all()
        perfiles = db.execute(stmt_perfiles).scalars().all()

        i = 0
        while len(canciones) < LIMITE and i < len(artistas):
            stmt_artistas = select(Cancion).join(Artista, Cancion.Artista_correo == artistas[i].correo
                ).order_by(Cancion.reproducciones.desc()
                ).limit(LIMITE - len(canciones))
            
            canciones += db.execute(stmt_artistas)
            i += 1

        i = 0
        while len(albumes) < LIMITE and i < len(artistas):
            stmt_artistas = select(Album).join(Artista, Album.Artista_correo == artistas[i].correo
                ).order_by(Album.nombre.asc()
                ).limit(LIMITE - len(albumes))
            
            albumes += db.execute(stmt_artistas)
            i += 1

        resultado = {
            "canciones": [{"fotoPortada":c.album.fotoPortada, "id": c.id, "nombre": c.nombre, 
                           "nombreArtisticoArtista":c.artista.nombreArtistico} for c in canciones],
            "albumes": [{"fotoPortada":a.fotoPortada, "id": a.id, "nombre": a.nombre,
                         "nombreArtisticoArtista":a.artista.nombreArtistico} for a in albumes],
            "playlists": [{"fotoPortada":p.fotoPortada, "id": p.id, "nombre": p.nombre,
                           "nombreUsuarioCreador":p.oyente.nombreUsuario} for p in playlists],
            "artistas": [{"fotoPerfil": a.fotoPerfil, "nombreArtistico": a.nombreArtistico, 
                          "nombreUsuario": a.nombreUsuario} for a in artistas],
            "perfiles": [{"fotoPerfil": p.fotoPerfil, 
                          "nombreUsuario": p.nombreUsuario} for p in perfiles]
        }

        return jsonify(resultado), 200


"""Devuelve una lista con los resultados de la búsqueda de usuarios que pueden invitarse a 
   una playlist (seguidores, no invitados ni participantes de esa misma playlist)"""
@search_bp.route("/search-invitados", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search_invitados():
    # Recuperar parametros peticion
    correo = get_jwt_identity()
    termino = request.args.get("termino").strip()
    termino_no_spaces = re.sub(r"\s+", "", termino)
    playlist = request.args.get("playlist").strip()
    if not playlist:
        return jsonify({"error": "Falta el ID de la playlist."}), 400 
    if not termino:
        return jsonify({"perfiles": []}), 200 
    
    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404

        stmt_perfiles = select(Oyente
            ).where(and_(
                Oyente.correo.in_(  # Seguidor
                    select(sigue_table.c.Seguidor_correo).where(sigue_table.c.Seguido_correo == correo)
                ),
                Oyente.correo.notin_(  # No participante
                    select(participante_table.c.Oyente_correo).where(participante_table.c.Playlist_id == playlist)
                ),
                Oyente.correo.notin_(   # No invitado
                    select(invitado_table.c.Oyente_correo).where(invitado_table.c.Playlist_id == playlist)
                ),
                Oyente.nombreUsuario.ilike(f"%{termino_no_spaces}%"))
            ).order_by(
                case((Oyente.nombreUsuario.ilike(f"{termino_no_spaces}%"), 1),
                else_=2), Oyente.nombreUsuario.asc()).limit(LIMITE)
                                             
        perfiles = db.execute(stmt_perfiles).scalars().all()
        resultados = [{"fotoPerfil": p.fotoPerfil, 
                       "nombreUsuario": p.nombreUsuario} for p in perfiles]
        
        return jsonify({"perfiles": resultados}), 200
    
"""Devuelve una lista con los resultados de la búsqueda de usuarios que pueden invitarse a 
   una playlist (seguidores, no invitados ni participantes de esa misma playlist)"""
@search_bp.route("/search-for-playlist", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search_for_playlist():
    # Recuperar parametros peticion
    termino = request.args.get("termino").strip()
    termino_no_spaces = re.sub(r"\s+", "", termino)
    playlist = request.args.get("playlist").strip()
    if not playlist:
        return jsonify({"error": "Falta el ID de la playlist."}), 400 
    if not termino:
        return jsonify({"canciones": []}), 200 

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        stmt_canciones = select(Cancion 
            ).where(and_(or_(
                Cancion.nombre.ilike(f"%{termino}%"),
                Cancion.album.ilike(f"%{termino}%")),
                Cancion.id.not_in(
                select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)))   
            ).order_by(
                case((Cancion.nombre.ilike(f"{termino}%"), 1), else_=2),  
                case((Cancion.album.ilike(f"{termino}%"), 1), else_=2), 
                Cancion.reproducciones.desc()
            ).limit(LIMITE)
        
        canciones = db.execute(stmt_canciones).scalars().all()

        if len(canciones) < LIMITE:
            stmt_artistas = select(Cancion).join(Artista, Cancion.Artista_correo == Artista.correo
                ).where(and_(or_(
                    Artista.nombreArtistico.ilike(f'{termino}%'), 
                    Artista.nombreUsuario.ilike(f'{termino_no_spaces}%')),
                    Cancion.id.not_in(
                    select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)))
                ).order_by(Cancion.reproducciones.desc()
                ).limit(LIMITE - len(canciones))
            
            canciones += db.execute(stmt_artistas)     

        resultados = [{"fotoPortada":c.album.fotoPortada, "id": c.id, "nombre": c.nombre, 
                      "nombreArtisticoArtista":c.artista.nombreArtistico} for c in canciones]

    return jsonify({"canciones": resultados}), 200
