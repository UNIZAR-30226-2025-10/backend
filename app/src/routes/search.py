from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, or_, case, and_, not_
from sqlalchemy.orm import selectinload
from db.db import get_db
from db.models import Cancion, Playlist, Album, Artista, Oyente, Sigue, invitado_table, participante_table, EsParteDePlaylist, featuring_table, GeneroMusical, pertenece_table
from utils.decorators import roles_required, tokenVersion_required
import re

search_bp = Blueprint('search', __name__) 

LIMITE = 20
MAX = 2

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
    if not termino:
        return jsonify({
            "canciones": [],"albumes": [],
            "playlists": [], "artistas": [], "perfiles": []
        }), 200 

    with get_db() as db:
        # Buscar canciones
        stmt_canciones = select(Cancion 
            ).where(
                Cancion.nombre.ilike(f"%{termino}%")
            ).options(
                selectinload(Cancion.album),  
                selectinload(Cancion.artista)
            ).order_by(
                case((Cancion.nombre.ilike(f"{termino}%"), 1), else_=2),
                Cancion.reproducciones.desc()
            ).limit(LIMITE)

        # Buscar albumes
        stmt_albumes = select(Album
            ).where(Album.nombre.ilike(f"%{termino}%")
            ).options(selectinload(Album.artista)
            ).order_by(
                case((Album.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Album.nombre.asc()
            ).limit(LIMITE)

        # Buscar playlists
        stmt_playlists = select(Playlist
            ).where(and_(Playlist.nombre.ilike(f"%{termino}%"),
                         Playlist.privacidad == False)
            ).options(selectinload(Playlist.oyente)
            ).order_by(
                case((Playlist.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Playlist.nombre.asc()
            ).limit(LIMITE)
        
        # Buscar artistas
        stmt_artistas = select(Artista
            ).where(or_(
                Artista.nombreArtistico.ilike(f"%{termino}%"), 
                Artista.nombreUsuario.ilike(f"%{termino_no_spaces}%"))
            ).order_by(
                case((Artista.nombreArtistico.ilike(f"{termino}%"), 1),  
                (Artista.nombreUsuario.ilike(f"{termino_no_spaces}%"), 2), else_=3), 
                Artista.nombreArtistico.asc(), 
                Artista.nombreUsuario.asc()
            ).limit(LIMITE)

        # Buscar perfiles
        stmt_perfiles = select(Oyente
            ).where(and_(
                Oyente.nombreUsuario.ilike(f"%{termino_no_spaces}%"), 
                not_(Oyente.tipo == "artista"))
            ).order_by(
                case((Oyente.nombreUsuario.ilike(f"{termino_no_spaces}%"), 1), else_=2), 
                Oyente.nombreUsuario.asc()
            ).limit(LIMITE)

        # Buscar géneros musicales
        stmt_generos = select(GeneroMusical
            ).where(
                GeneroMusical.nombre.ilike(f"%{termino}%")
            ).order_by(
                case((GeneroMusical.nombre.ilike(f"{termino}%"), 1), else_=2),
                GeneroMusical.nombre.asc()
            ).limit(LIMITE)

        canciones = db.execute(stmt_canciones).scalars().all()
        canciones_id = {c.id for c in canciones}
        albumes = db.execute(stmt_albumes).scalars().all()
        albumes_id = {a.id for a in albumes}
        playlists = db.execute(stmt_playlists).scalars().all()
        playlists_id = {p.id for p in playlists}
        artistas = db.execute(stmt_artistas).scalars().all()
        artistas_correos = {a.correo for a in artistas}
        perfiles = db.execute(stmt_perfiles).scalars().all()
        perfiles_correos = {p.correo for p in perfiles}
        generos = db.execute(stmt_generos).scalars().all()

        # Busca genero musical
        if len(generos) > 0 and len(canciones) < MAX:
            # Añadir canciones del genero buscado
            i = 0
            while len(canciones) < LIMITE and i < len(generos):
                stmt_canciones = select(Cancion
                    ).join(pertenece_table, pertenece_table.c.Cancion_id == Cancion.id
                    ).where(and_(
                        pertenece_table.c.GeneroMusical_nombre == generos[i].nombre,
                        Cancion.id.notin_(canciones_id))
                    ).options(
                        selectinload(Cancion.album),  
                        selectinload(Cancion.artista)
                    ).order_by(Cancion.reproducciones.desc()
                    ).limit(LIMITE - len(canciones))
                
                nuevas_canciones = db.execute(stmt_canciones).scalars().all()
                canciones += nuevas_canciones
                canciones_id.update(p.id for p in nuevas_canciones)
                i += 1

        # Busca artista
        elif len(artistas) > 0 and len(artistas) < MAX:
            # Añadir canciones del artista buscado
            i = 0
            while len(canciones) < LIMITE and i < len(artistas):
                stmt_artistas = select(Cancion
                    ).where(and_(
                        Cancion.Artista_correo == artistas[i].correo,
                        Cancion.id.notin_(canciones_id))
                    ).options(
                        selectinload(Cancion.album),  
                        selectinload(Cancion.artista)
                    ).order_by(Cancion.reproducciones.desc()
                    ).limit(LIMITE - len(canciones))
                
                nuevas_canciones = db.execute(stmt_artistas).scalars().all()
                canciones += nuevas_canciones
                canciones_id.update(c.id for c in nuevas_canciones)
                i += 1

            # Añadir albumes del artista buscado
            i = 0
            while len(albumes) < LIMITE and i < len(artistas):
                stmt_artistas = select(Album
                    ).where(and_(
                        Album.Artista_correo == artistas[i].correo,
                        Album.id.notin_(albumes_id))
                    ).options(selectinload(Album.artista)
                    ).order_by(Album.nombre.asc()
                    ).limit(LIMITE - len(albumes))
                
                nuevos_albumes = db.execute(stmt_artistas).scalars().all()
                albumes += nuevos_albumes
                albumes_id.update(a.id for a in nuevos_albumes)
                i += 1
            
            # Añadir playlists del artista buscado
            i = 0
            while len(playlists) < LIMITE and i < len(artistas):
                stmt_playlists = select(Playlist
                    ).where(and_(
                        Playlist.Oyente_correo == artistas[i].correo,
                        Playlist.privacidad == False,
                        Playlist.id.notin_(playlists_id))
                    ).options(selectinload(Playlist.oyente)
                    ).order_by(Playlist.fecha.desc()
                    ).limit(LIMITE - len(playlists))
                
                nuevas_playlists = db.execute(stmt_playlists).scalars().all()
                playlists += nuevas_playlists
                playlists_id.update(p.id for p in nuevas_playlists)
                i += 1

        # Busca perfil
        elif len(perfiles) > 0 and len(perfiles) < MAX:
            # Añadir playlists del perfil buscado
            i = 0
            while len(playlists) < LIMITE and i < len(perfiles):
                stmt_playlists = select(Playlist
                    ).where(and_(
                        Playlist.Oyente_correo == perfiles[i].correo,
                        Playlist.privacidad == False,
                        Playlist.id.notin_(playlists_id))
                    ).options(selectinload(Playlist.oyente)
                    ).order_by(Playlist.fecha.desc()
                    ).limit(LIMITE - len(playlists))
                
                nuevas_playlists = db.execute(stmt_playlists).scalars().all()
                playlists += nuevas_playlists
                playlists_id.update(p.id for p in nuevas_playlists)
                i += 1

        # Busca album
        elif len(albumes) > 0 and len(albumes) < MAX:
            # Añadir canciones del album buscado 
            i = 0
            while len(canciones) < LIMITE and i < len(albumes):
                stmt_albumes = select(Cancion
                    ).where(and_(
                        Cancion.Album_id == albumes[i].id,
                        Cancion.id.notin_(canciones_id))
                    ).options(
                        selectinload(Cancion.album),  
                        selectinload(Cancion.artista)
                    ).order_by(Cancion.reproducciones.desc()
                    ).limit(LIMITE - len(canciones))
                
                nuevas_canciones = db.execute(stmt_albumes).scalars().all()
                canciones += nuevas_canciones
                canciones_id.update(c.id for c in nuevas_canciones)
                i += 1

            # Añadir artista del album buscado
            i = 0
            while len(artistas) < LIMITE and i < len(albumes):            
                if albumes[i].Artista_correo not in artistas_correos:
                    artistas += [albumes[i].artista]
                    artistas_correos.add(albumes[i].Artista_correo)
                i += 1

            # Añadir playlists del album buscado
            i = 0
            while len(playlists) < LIMITE and i < len(albumes):
                stmt_playlists = select(Playlist
                    ).join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id
                    ).join(Cancion, EsParteDePlaylist.Cancion_id == Cancion.id
                    ).where(and_(
                        Cancion.Album_id == albumes[i].id,
                        Playlist.id.notin_(playlists_id),
                        Playlist.privacidad == False)
                    ).options(selectinload(Playlist.oyente)
                    ).distinct(
                    ).order_by(Playlist.fecha.desc()
                    ).limit(LIMITE - len(playlists))
                
                nuevas_playlists = db.execute(stmt_playlists).scalars().all()
                playlists += nuevas_playlists
                playlists_id.update(p.id for p in nuevas_playlists)
                i += 1
        
        # Busca cancion
        elif len(canciones) > 0 and len(canciones) < MAX:
            # Añadir artistas de la cancion buscada
            i = 0
            while len(artistas) < LIMITE and i < len(canciones):
                if canciones[i].Artista_correo not in artistas_correos:
                    artistas += [canciones[i].artista]
                    artistas_correos.add(canciones[i].Artista_correo)
                            
                nuevos_artistas = db.execute(select(Artista).join(featuring_table, Artista.correo == featuring_table.c.Artista_correo
                                                ).where(and_(or_(featuring_table.c.Cancion_id == canciones[i].id),
                                                                Artista.correo.notin_(artistas_correos))).limit(LIMITE - len(artistas))
                                                ).scalars().all()
                artistas += nuevos_artistas
                artistas_correos.update(a.correo for a in nuevos_artistas)
                i += 1
            
            # Añadir album de la cancion buscada
            i = 0
            while len(albumes) < LIMITE and i < len(canciones):
                if canciones[i].Album_id not in albumes_id:
                    albumes += [canciones[i].album]
                    albumes_id.add(canciones[i].Album_id)
                i += 1

            # Añadir playlists de la cancion buscada
            i = 0
            while len(playlists) < LIMITE and i < len(canciones):
                stmt_playlists = select(Playlist
                    ).join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id
                    ).where(and_(
                        EsParteDePlaylist.Cancion_id == canciones[i].id,
                        Playlist.id.notin_(playlists_id),
                        Playlist.privacidad == False)
                    ).options(selectinload(Playlist.oyente)
                    ).order_by(Playlist.fecha.desc()
                    ).limit(LIMITE - len(playlists))
                
                nuevas_playlists = db.execute(stmt_playlists).scalars().all()
                playlists += nuevas_playlists
                playlists_id.update(p.id for p in nuevas_playlists)
                i += 1

        # Busca playlist
        elif len(playlists) > 0 and len(playlists) < MAX:
            # Añadir canciones de la playlist buscada
            i = 0
            while len(canciones) < LIMITE and i < len(playlists):
                stmt_canciones = select(Cancion
                    ).join(EsParteDePlaylist, EsParteDePlaylist.Cancion_id == Cancion.id
                    ).where(and_(
                        EsParteDePlaylist.Playlist_id == playlists[i].id,
                        Cancion.id.notin_(canciones_id))
                    ).options(
                        selectinload(Cancion.album),  
                        selectinload(Cancion.artista)
                    ).order_by(EsParteDePlaylist.fecha
                    ).limit(LIMITE - len(canciones))
                
                nuevas_canciones = db.execute(stmt_canciones).scalars().all()
                canciones += nuevas_canciones
                canciones_id.update(p.id for p in nuevas_canciones)
                i += 1
            
            # Añadir albumes de la playlist
            i = 0
            while len(albumes) < LIMITE and i < len(playlists):
                stmt_albumes = select(Album
                    ).join(EsParteDePlaylist, EsParteDePlaylist.Cancion_id == Cancion.id
                    ).join(Cancion, Cancion.Album_id == Album.id
                    ).where(and_(
                        EsParteDePlaylist.Playlist_id == playlists[i].id,
                        Album.id.notin_(albumes_id))
                    ).options(selectinload(Album.artista)
                    ).distinct(
                    ).order_by(EsParteDePlaylist.fecha
                    ).limit(LIMITE - len(albumes))
                
                nuevos_albumes = db.execute(stmt_albumes).scalars().all()
                albumes += nuevos_albumes
                albumes_id.update(p.id for p in nuevos_albumes)
                i += 1

            # Añadir perfiles de la playlist
            i = 0
            while len(perfiles) < LIMITE and i < len(playlists):
                if playlists[i].Oyente_correo not in perfiles_correos:
                    perfiles += [playlists[i].oyente]
                    perfiles_correos.add(playlists[i].Oyente_correo)

                nuevos_perfiles = db.execute(select(Oyente).join(participante_table, Oyente.correo == participante_table.c.Oyente_correo
                                                ).where(and_(or_(participante_table.c.Playlist_id == playlists[i].id),
                                                                Oyente.correo.notin_(perfiles_correos))).limit(LIMITE - len(perfiles))
                                                ).scalars().all()
                perfiles += nuevos_perfiles
                perfiles_correos.update(p.correo for p in nuevos_perfiles)
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
    playlist = request.args.get("playlist")
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
                    select(Sigue.Seguidor_correo).where(Sigue.Seguido_correo == correo)
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
    
"""Devuelve una lista con los resultados de la búsqueda de canciones que pueden
   añadirse a una playlist"""
@search_bp.route("/search-for-playlist", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search_for_playlist():
    # Recuperar parametros peticion
    termino = request.args.get("termino").strip()
    termino_no_spaces = re.sub(r"\s+", "", termino)
    playlist = request.args.get("playlist")
    if not playlist:
        return jsonify({"error": "Falta el ID de la playlist."}), 400 
    if not termino:
        return jsonify({"canciones": []}), 200 

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        stmt_canciones = select(Cancion 
            ).where(and_(
                Cancion.nombre.ilike(f"%{termino}%"),
                Cancion.id.notin_(
                select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)))
            ).options(
                selectinload(Cancion.album),  
                selectinload(Cancion.artista)   
            ).order_by(
                case((Cancion.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Cancion.reproducciones.desc()
            ).limit(LIMITE)
        
        canciones = db.execute(stmt_canciones).scalars().all()
        canciones_id = {c.id for c in canciones}

        # Añadir canciones del artista buscado
        if len(canciones) < LIMITE:
            stmt_artistas = select(Cancion).join(Artista, Cancion.Artista_correo == Artista.correo
                ).where(and_(or_(
                    Artista.nombreArtistico.ilike(f'{termino}%'), 
                    Artista.nombreUsuario.ilike(f'{termino_no_spaces}%')),
                    Cancion.id.notin_(
                    select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)), 
                    Cancion.id.notin_(canciones_id))
                ).options(
                    selectinload(Cancion.album),  
                    selectinload(Cancion.artista)
                ).order_by(
                    case((Artista.nombreArtistico.ilike(f"{termino}%"), 1),  
                    (Artista.nombreUsuario.ilike(f"{termino_no_spaces}%"), 2), else_=3),
                    Cancion.reproducciones.desc()
                ).limit(LIMITE - len(canciones))
            
            canciones += db.execute(stmt_artistas).scalars().all()    

        # Añadir canciones del album buscado
        if len(canciones) < LIMITE:
            stmt_albumes = select(Cancion).join(Album, Cancion.Album_id == Album.id
                ).where(and_(
                    Album.nombre.ilike(f"%{termino}%"),
                    Cancion.id.notin_(
                    select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)),
                    Cancion.id.notin_(canciones_id))
                ).options(
                    selectinload(Cancion.album),  
                    selectinload(Cancion.artista)
                ).order_by(
                    case((Album.nombre.ilike(f"{termino}%"), 1), else_=2),
                    Cancion.reproducciones.desc()
                ).limit(LIMITE - len(canciones))
            
            canciones += db.execute(stmt_albumes).scalars().all() 

        # Añadir canciones del género buscado
        if len(canciones) < LIMITE:
            stmt_genero = select(Cancion).join(pertenece_table, pertenece_table.c.Cancion_id == Cancion.id
                ).join(
                    GeneroMusical, pertenece_table.c.GeneroMusical_nombre == GeneroMusical.nombre
                ).where(and_(
                    GeneroMusical.nombre.ilike(f"%{termino}%"),
                    Cancion.id.notin_(
                        select(EsParteDePlaylist.Cancion_id).where(EsParteDePlaylist.Playlist_id == playlist)
                    ),
                    Cancion.id.notin_(canciones_id)
                )).options(
                    selectinload(Cancion.album),
                    selectinload(Cancion.artista)
                ).order_by(
                    case((GeneroMusical.nombre.ilike(f"{termino}%"), 1), else_=2),
                    Cancion.reproducciones.desc()
                ).limit(LIMITE - len(canciones))

            canciones += db.execute(stmt_genero).scalars().all()

        resultados = [{"fotoPortada":c.album.fotoPortada, "id": c.id, "nombre": c.nombre, 
                      "nombreArtisticoArtista":c.artista.nombreArtistico} for c in canciones]

    return jsonify({"canciones": resultados}), 200


"""Devuelve una lista con los resultados de la búsqueda de canciones que pueden
   añadirse a un noizzy"""
@search_bp.route("/search-for-noizzy", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def search_for_noizzy():
    # Recuperar parametros peticion
    termino = request.args.get("termino").strip()
    termino_no_spaces = re.sub(r"\s+", "", termino)
    if not termino:
        return jsonify({"canciones": []}), 200 

    with get_db() as db:      
        stmt_canciones = select(Cancion 
            ).where(Cancion.nombre.ilike(f"%{termino}%")
            ).options(
                selectinload(Cancion.album),  
                selectinload(Cancion.artista)
            ).order_by(
                case((Cancion.nombre.ilike(f"{termino}%"), 1), else_=2), 
                Cancion.reproducciones.desc()
            ).limit(LIMITE)
        
        canciones = db.execute(stmt_canciones).scalars().all()

        resultados = [{"fotoPortada":c.album.fotoPortada, "id": c.id, "nombre": c.nombre, 
                      "nombreArtisticoArtista":c.artista.nombreArtistico} for c in canciones]

    return jsonify({"canciones": resultados}), 200
