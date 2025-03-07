from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select, or_, case, and_, not_
from db.db import get_db
from db.models import Cancion, Playlist, Album, Artista, Oyente
from utils.decorators import roles_required, tokenVersion_required

search_bp = Blueprint('search', __name__) 


"""Devuelve 4 listas con las canciones, albumes, playlists y artistas
   que empiezan por el termino buscado"""
@search_bp.route("/search", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search():
    # Recuperar parametros peticion
    termino = request.args.get("termino").strip()
    if not termino :
        return jsonify({
            "canciones": [],"albumes": [],
            "playlists": [], "artsitas": []
        }), 200 

    with get_db() as db:
        # Buscar canciones
        stmt_canciones = select(Cancion).where(Cancion.nombre.ilike(f"%{termino}%")).order_by(
            case((Cancion.nombre.ilike(f"{termino}%"), 1),
            else_=2), Cancion.nombre.asc()).limit(20)

        stmt_albumes = select(Album).where(Album.nombre.ilike(f"%{termino}%")).order_by(
            case((Album.nombre.ilike(f"{termino}%"), 1),
            else_=2), Album.nombre.asc()).limit(20)

        stmt_playlists = select(Playlist).where(Playlist.nombre.ilike(f"%{termino}%")).order_by(
            case((Playlist.nombre.ilike(f"{termino}%"), 1),
            else_=2), Playlist.nombre.desc()).limit(20)
        
        stmt_artistas = select(Artista).where(or_(Artista.nombreArtistico.ilike(f"%{termino}%"), 
                                              Artista.nombreUsuario.ilike(f"%{termino}%"))).order_by(
            case((Artista.nombreArtistico.ilike(f"{termino}%"), 1),  
            (Artista.nombreUsuario.ilike(f"{termino}%"), 2),  
            else_=3), Artista.nombreArtistico.asc(), Artista.nombreUsuario.asc()).limit(20)
        
        stmt_perfiles = select(Oyente).where(and_(Oyente.nombreUsuario.ilike(f"%{termino}%"), 
                                              not_(Oyente.tipo == "artista"))).order_by(
            case((Oyente.nombreUsuario.ilike(f"{termino}%"), 1),
            else_=2), Oyente.nombreUsuario.desc()).limit(20)
                                             

        canciones = db.execute(stmt_canciones).scalars().all()
        albumes = db.execute(stmt_albumes).scalars().all()
        playlists = db.execute(stmt_playlists).scalars().all()
        artistas = db.execute(stmt_artistas).scalars().all()
        perfiles = db.execute(stmt_perfiles).scalars().all()

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
