from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload
from db.models import EstaEscuchandoCancion, EstaEscuchandoColeccion, Oyente, Playlist, EsParteDePlaylist, HistorialCancion, HistorialColeccion, Cancion, GeneroMusical, Artista, notificacionCancion_table
from db.db import get_db
from utils.decorators import roles_required, tokenVersion_required
from utils.fav import fav
from utils.estadisticas import estadisticas_song
from datetime import datetime
import pytz
import os
import cloudinary.uploader
from .websocket import socketio


song_bp = Blueprint('song', __name__)

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)


"""Devuelve la cancion actual"""
@song_bp.route("/get-cancion-actual", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def get_cancion_actual():
    correo = get_jwt_identity()
    
    with get_db() as db:
        # Recuperar cancion y coleccion que se esta escuchando
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)
        if estaEscuchandoCancion_entry:
            cancion = estaEscuchandoCancion_entry.cancion
            cancion_dict = {
                    "id": cancion.id,
                    "audio": cancion.audio,
                    "nombre": cancion.nombre,
                    "nombreArtisticoArtista": cancion.artista.nombreArtistico,
                    "nombreUsuarioArtista": cancion.artista.nombreUsuario,
                    "progreso": estaEscuchandoCancion_entry.progreso,
                    "featuring": [f.nombreArtistico for f in cancion.featuring],
                    "fav": fav(cancion.id, correo, db),
                    "fotoPortada": cancion.album.fotoPortada
                }
            
            estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)
            if estaEscuchandoColeccion_entry:
                coleccion = estaEscuchandoColeccion_entry
                if coleccion.modo == "aleatorio":
                    if coleccion.coleccion.tipo == "playlist":
                        ordenNatural = db.execute(select(EsParteDePlaylist.Cancion_id
                                                         ).where(EsParteDePlaylist.Playlist_id == coleccion.Coleccion_id).order_by(EsParteDePlaylist.fecha.asc())
                                                 ).scalars().all()
                    else:
                        ordenNatural = db.execute(select(Cancion.id
                                                         ).where(Cancion.Album_id == coleccion.Coleccion_id).order_by(Cancion.puesto.asc())
                                                 ).scalars().all()
                else:
                    ordenNatural = None

                coleccion_dict = {
                        "id": coleccion.Coleccion_id,
                        "orden": coleccion.orden,
                        "ordenNatural": ordenNatural,
                        "index": coleccion.index,                      
                        "modo": coleccion.modo
                    }
            else: 
                coleccion_dict = None

        else: 
            cancion_dict = None
            coleccion_dict = None
        
    return jsonify({"cancion": cancion_dict, "coleccion": coleccion_dict}), 200


"""Actualiza el progreso de la cancion actual"""
@song_bp.route("/change-progreso", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def change_progreso():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400
    
    correo = get_jwt_identity()
    progreso = data.get("progreso")
    if progreso is None:
        return jsonify({"error": "Falta el progreso de la cancion."}), 400 
    
    with get_db() as db:
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)
        if not estaEscuchandoCancion_entry:
            return jsonify({"error": "El usuario no esta reproduciendo ninguna cancion."}), 404 

        if progreso < 0 or progreso > estaEscuchandoCancion_entry.cancion.duracion:
            return jsonify({"error": "Progreso no valido."}), 400 

        estaEscuchandoCancion_entry.progreso = progreso       
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    return jsonify(""), 200


"""Cambia el modo de reproduccion de la cancion actual"""
@song_bp.route("/change-modo", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def change_modo():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    modo = data.get("modo")
    orden = data.get("orden")
    index = data.get("index")
    if not modo or not orden or index is None:
        return jsonify({"error": "Falta el modo de la cancion."}), 400 
    
    if modo not in ["aleatorio", "enOrden"]:
        return jsonify({"error": "Modo incorrecto."}), 400 

    if index > len(orden):
        return jsonify({"error": "Index no valido."}), 400 

    with get_db() as db:
        estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)
        if not estaEscuchandoColeccion_entry:
            return jsonify({"error": "El usuario no esta reproduciendo ninguna cancion en una coleccion."}), 404 

        estaEscuchandoColeccion_entry.modo = modo
        estaEscuchandoColeccion_entry.orden = orden
        estaEscuchandoColeccion_entry.index = index

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

    return jsonify(""), 200


"""Inserta o borra una cancion de la lista de Favoritos del usuario"""
@song_bp.route("/change-fav", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def change_fav():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    cancion_id = data.get("id")
    fav = data.get("fav")
    if not cancion_id or fav is None:
        return jsonify({"error": "Faltan campos en la peticion."}), 400 

    with get_db() as db:
        stmt = select(Playlist.id).filter(Playlist.nombre == "Favoritos", Playlist.Oyente_correo == correo)
        playlist_id = db.execute(stmt).scalars().first()
        if not playlist_id:
            return jsonify({"error": "No existe playlist Favoritos."}), 404

        fav_entry = db.get(EsParteDePlaylist, (cancion_id, playlist_id))
        
        if fav and not fav_entry:
            # Si no esta en Favoritos y fav == True, agregarla
            new_entry = EsParteDePlaylist(Cancion_id=cancion_id, Playlist_id=playlist_id, fecha=datetime.now(pytz.timezone('Europe/Madrid')))
            db.add(new_entry)

        elif not fav and fav_entry:
            # Si esta en Favoritos y fav == False, eliminarla
            db.delete(fav_entry)

        elif fav_entry:
            return jsonify({"error": "La cancion ya esta en favoritos."}), 409

        else:
            return jsonify({"error": "La cancion no esta en favoritos."}), 404

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 200


"""Incrementa el numero de reproducciones de una cancion"""
@song_bp.route("/add-reproduccion", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def add_reproduccion():
    correo = get_jwt_identity()
    
    with get_db() as db:
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)
        if not estaEscuchandoCancion_entry:
            return jsonify({"error": "El usuario no esta reproduciendo ninguna cancion."}), 404 

        cancion = estaEscuchandoCancion_entry.cancion
        # Incrementar numero de reproducciones
        cancion.reproducciones += 1

        # Actualizar historial de canciones
        historialCancion_entry = db.get(HistorialCancion, (correo, cancion.id))
        if not historialCancion_entry:
            historialCancion_entry = HistorialCancion(Oyente_correo=correo, Cancion_id=cancion.id, 
                                                      fecha=datetime.now(pytz.timezone('Europe/Madrid')))
            db.add(historialCancion_entry)
        else:
            historialCancion_entry.fecha=datetime.now(pytz.timezone('Europe/Madrid'))
        
        estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)
        if estaEscuchandoColeccion_entry:
            # Actualizar historial de colecciones
            historialColeccion_entry = db.get(HistorialCancion, (correo, estaEscuchandoColeccion_entry.Coleccion_id))
            if not historialColeccion_entry:
                historialColeccion_entry = HistorialColeccion(Oyente_correo=correo, fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                                                              Coleccion_id=estaEscuchandoColeccion_entry.Coleccion_id)
                db.add(historialColeccion_entry)
            else:
                historialColeccion_entry.fecha=datetime.now(pytz.timezone('Europe/Madrid'))
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 200


"""Reproduce una cancion sola"""
@song_bp.route("/put-cancion-sola", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def put_cancion_sola():    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    cancion_id = data.get("id")
    if not cancion_id:
        return jsonify({"error": "Faltan campos en la peticion."}), 400 

    with get_db() as db:
        # Recuperar cancion actual
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)

        # 1ª cancion actual
        if not estaEscuchandoCancion_entry:
            estaEscuchandoCancion_entry = EstaEscuchandoCancion(Oyente_correo=correo, Cancion_id=cancion_id, 
                                                                progreso=0)
            db.add(estaEscuchandoCancion_entry)
        
        # Actualizar cancion actual
        else:
            estaEscuchandoCancion_entry.Cancion_id = cancion_id
            estaEscuchandoCancion_entry.progreso = 0
        
            # Recuperar coleccion actual
            estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)

            # Quitar coleccion actual
            if estaEscuchandoColeccion_entry:
                db.delete(estaEscuchandoColeccion_entry)
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
        
        return jsonify({"audio": estaEscuchandoCancion_entry.cancion.audio,
                "nombreUsuarioArtista": estaEscuchandoCancion_entry.cancion.artista.nombreUsuario,
                "featuring": [f.nombreArtistico for f in estaEscuchandoCancion_entry.cancion.featuring],
                "fav": fav(cancion_id, correo, db)}), 200

"""Reproduce una cancion en una coleccion"""
@song_bp.route("/put-cancion-coleccion", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def put_cancion_coleccion():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    coleccion_id = data.get("coleccion")
    modo = data.get("modo")
    orden = data.get("orden")
    index = data.get("index")
    if not coleccion_id or not modo or not orden or index is None:
        return jsonify({"error": "Faltan campos en la peticion."}), 400 

    if modo not in ["aleatorio", "enOrden"]:
        return jsonify({"error": "Modo no valido."}), 400 

    if index > len(orden):
        return jsonify({"error": "Index no valido."}), 400 

    cancion_id = orden[index]
    with get_db() as db:
        # Recuperar cancion actual
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)

        # 1ª cancion actual
        if not estaEscuchandoCancion_entry:
            estaEscuchandoCancion_entry = EstaEscuchandoCancion(Oyente_correo=correo, Cancion_id=cancion_id, 
                                                                progreso=0)
            db.add(estaEscuchandoCancion_entry)
        
        # Actualizar cancion actual
        else:
            estaEscuchandoCancion_entry.Cancion_id = cancion_id
            estaEscuchandoCancion_entry.progreso = 0

            # Recuperar coleccion actual
            estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)

            # Nueva coleccion actual
            if not estaEscuchandoColeccion_entry:
                estaEscuchandoColeccion_entry = EstaEscuchandoColeccion(Oyente_correo=correo, Coleccion_id=coleccion_id, 
                                                                    modo=modo, orden=orden, index=index)
                db.add(estaEscuchandoColeccion_entry)
            
            # Actualizar coleccion actual
            else:
                estaEscuchandoColeccion_entry.Coleccion_id = coleccion_id
                estaEscuchandoColeccion_entry.modo = modo
                estaEscuchandoColeccion_entry.orden = orden
                estaEscuchandoColeccion_entry.index = index

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        return jsonify({"audio": estaEscuchandoCancion_entry.cancion.audio,
                "nombreUsuarioArtista": estaEscuchandoCancion_entry.cancion.artista.nombreUsuario,
                "featuring": [f.nombreArtistico for f in estaEscuchandoCancion_entry.cancion.featuring],
                "fav": fav(cancion_id, correo, db)}), 200
    
"""Sube una nueva cancion"""
@song_bp.route("/create-cancion", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def create_cancion():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400
    
    artista = get_jwt_identity()
    nombre = data.get("nombre")
    duracion = data.get("duracion")
    audio_url = data.get("audio_url")
    album_id = data.get("album_id")
    tags = data.get("tags")
    artistasFt = data.get("artistasFt")

    if not nombre or not artista or not album_id or not duracion or not audio_url or not tags or not artistasFt:
        return jsonify({
        "error": "Faltan datos de la canción.",
        "nombre": nombre,
        "artista": artista,
        "album_id": album_id,
        "duracion": duracion,
        "audio_url": audio_url,
        "tags": tags,
        "artistasFt": artistasFt
    }), 400

    if not tags or len(tags) < 1 or len(tags) > 3:
        return jsonify({"error": "Debe haber entre 1 y 3 tags."}), 400
    
    # Funcion auxiliar para obtener el último puesto de un album
    def obtener_ultimo_puesto(session, album_id, artista_correo):
        # Obtener todas las canciones del álbum del artista
        canciones = session.query(Cancion).filter_by(Album_id=album_id, Artista_correo=artista_correo).all()
        
        if not canciones:
            return 0  # Si no hay canciones, devolver 0

        ultimo_puesto = max(cancion.puesto for cancion in canciones)
        return ultimo_puesto

    # Guardar la información de la canción en la base de datos
    with get_db() as db:
        nueva_cancion = Cancion(
            Artista_correo=artista,
            nombre=nombre,
            duracion=int(duracion),
            audio=audio_url,
            fecha=datetime.now(pytz.timezone('Europe/Madrid')),
            reproducciones=0,
            Album_id=album_id,
            puesto=obtener_ultimo_puesto(db, album_id, artista) + 1
        )

        db.add(nueva_cancion)
        db.flush()

        # Añadir los tags
        for tag in tags:
            genero = db.get(GeneroMusical, tag)
            nueva_cancion.generosMusicales.append(genero)

        for artistaFt in artistasFt:
            if not artistaFt.strip():  # Ignorar valores vacíos o solo espacios
                continue
            artista_entry = db.query(Artista).filter_by(nombreArtistico=artistaFt).first()
            if artista_entry:
                nueva_cancion.featuring.append(artista_entry)
            else:
                return jsonify({"error": f"El artista '{artistaFt}' no existe."}), 404

        artista_actual = db.get(Artista, artista, options=[selectinload(Artista.seguidores)])
        notificaciones = [
            {"Oyente_correo": seguidor.correo, "Cancion_id": nueva_cancion.id}
            for seguidor in artista_actual.seguidores
        ]
        if notificaciones:
            db.execute(insert(notificacionCancion_table), notificaciones)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        # Websockets para notificacion en tiempo real
        for seguidor in artista_actual.seguidores:
            socketio.emit("novedad-musical-ws", {"id": nueva_cancion.id,
                                                "nombre": nueva_cancion.nombre,
                                                "fotoPortada": nueva_cancion.album.fotoPortada,
                                                "nombreArtisticoArtista": nueva_cancion.artista.nombreArtistico,
                                                "featuring": [f.nombreArtistico for f in nueva_cancion.featuring]}
                                                , room=seguidor.correo)

        return jsonify(""), 201
      

"""Borra una canción dado su ID"""
@song_bp.route("/delete-cancion", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def delete_cancion():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el ID de la canción."}), 400

    try:
        with get_db() as db:
            # Obtener la canción
            cancion = db.get(Cancion, id)
            if not cancion:
                return jsonify({"error": "La canción no existe."}), 404

            audio_url = cancion.audio
            public_id = audio_url.split('/')[-2] + '/' + audio_url.split('/')[-1].split('.')[0]

            # Borrar la canción de la base de datos
            db.delete(cancion)

            try:
                cloudinary.uploader.destroy(public_id, resource_type="video")
            except Exception as e:
                return f"Error al eliminar la canción de Cloudinary: {e}"

            db.commit()

        return jsonify(""), 204

    except Exception as e:
        return jsonify({"error": f"Error al borrar la canción: {e}"}), 500
    

"""Devuelve las estadísticas de una canción para su artista"""
@song_bp.route("/get-estadisticas-cancion", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_estadisticas_cancion():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el ID de la cancion."}), 400
    correo = get_jwt_identity()
    
    with get_db() as db:
        cancion_entry = db.get(Cancion, id)
        if not cancion_entry:
            return jsonify({"error": "La cancion no existe."}), 404
        if cancion_entry.artista.correo != correo and not cancion_entry.artista in cancion_entry.featuring:
            return jsonify({"error": "El artista no puede consultar las estadisticas de esta cancion."}), 403
        
        n_playlists, favs = estadisticas_song(cancion_entry, db)
        cancion = {
            "audio": cancion_entry.audio,
            "nombre": cancion_entry.nombre,
            "album": cancion_entry.album.nombre,
            "duracion": cancion_entry.duracion,
            "fechaPublicacion": cancion_entry.fecha,
            "reproducciones": cancion_entry.reproducciones,
            "fotoPortada": cancion_entry.album.fotoPortada,
            "nPlaylists": n_playlists,
            "favs": favs
        }
        
    return jsonify({"cancion": cancion}), 200


"""Devuelve la lista de personas que han dado like a una canción del artista logueado"""
@song_bp.route("/get-estadisticas-favs", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_estadisticas_favs():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el ID de la cancion."}), 400
    correo = get_jwt_identity()
    
    with get_db() as db:
        cancion_entry = db.get(Cancion, id)
        if not cancion_entry:
            return jsonify({"error": "La cancion no existe."}), 404
        if cancion_entry.artista.correo != correo and not cancion_entry.artista in cancion_entry.featuring:
            return jsonify({"error": "El artista no puede consultar las estadisticas de esta cancion."})
        
        stmt = (
            select(Oyente)
            .join(Playlist, Playlist.Oyente_correo == Oyente.correo)
            .join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id)
            .where(
                Playlist.nombre == "Favoritos",
                EsParteDePlaylist.Cancion_id == id
            )
            .distinct()
        )

        oyentes = db.scalars(stmt).all()

        oyentes_favs = [
            {
                "nombreUsuario": oyente.nombreUsuario,
                "fotoPerfil": oyente.fotoPerfil
            }
            for oyente in oyentes
        ]
        
    return jsonify({"oyentes_favs": oyentes_favs}), 200


"""Devuelve la lista de personas que han dado like a una canción del artista logueado"""
@song_bp.route("/get-estadisticas-playlists", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_estadisticas_playlists():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el ID de la cancion."}), 400
    correo = get_jwt_identity()
    
    with get_db() as db:
        cancion_entry = db.get(Cancion, id)
        if not cancion_entry:
            return jsonify({"error": "La cancion no existe."}), 404
        if cancion_entry.artista.correo != correo and not cancion_entry.artista in cancion_entry.featuring:
            return jsonify({"error": "El artista no puede consultar las estadisticas de esta cancion."}), 403
        
        stmt = (
            select(Playlist)
            .join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id)
            .where(
                EsParteDePlaylist.Cancion_id == id,
                Playlist.privacidad == False
            )
            .distinct()
        )

        playlists_publicas = db.scalars(stmt).all()

        publicas = [
            {
                "id": playlist.id,
                "nombre": playlist.nombre,
                "fotoPortada": playlist.fotoPortada,
                "creador": playlist.oyente.nombreUsuario
            }
            for playlist in playlists_publicas
        ]

        stmt = (
            select(Playlist)
            .join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id)
            .where(
                EsParteDePlaylist.Cancion_id == id,
                Playlist.privacidad == True
            )
            .distinct()
        )

        n_playlists_privadas = len(db.scalars(stmt).all())
        
    return jsonify({"n_privadas": n_playlists_privadas,
                    "playlists_publicas": publicas}), 200


"""Devuelve una lista con todos los tags (géneros musicales)"""
@song_bp.route("/get-tags", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_tags():
    with get_db() as db:
        tags = db.query(GeneroMusical.nombre).all()
        tags_list = [tag[0] for tag in tags]  # Extraer solo los nombres de los géneros musicales

    return jsonify({"tags": tags_list}), 200


"""Devuelve informacion de una cancion"""
@song_bp.route("/get-data-cancion", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def get_cancion():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta la cancion."}), 400
    
    with get_db() as db:
        # Obtener la canción
        cancion = db.get(Cancion, id)
        if not cancion:
            return jsonify({"error": "La canción no existe."}), 401
        
        return jsonify({
            "nombre":cancion.nombre,
            "nombreArtisticoArtista": cancion.artista.nombreArtistico,
            "fotoPortada": cancion.album.fotoPortada
            }), 200