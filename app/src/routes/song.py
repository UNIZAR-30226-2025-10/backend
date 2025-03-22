from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select
from db.models import EstaEscuchandoCancion, EstaEscuchandoColeccion, Playlist, EsParteDePlaylist, HistorialCancion, HistorialColeccion, Cancion, GeneroMusical
from db.db import get_db
from utils.decorators import roles_required, tokenVersion_required, sid_required
from utils.fav import fav
from datetime import datetime
from .websocket import socketio
import pytz
import os
import cloudinary.uploader


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
def get_cancion():
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
                    "fav": fav(cancion.id, correo, db),
                    "fotoPortada": cancion.album.fotoPortada
                }
            
            estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)
            if estaEscuchandoColeccion_entry:
                coleccion = estaEscuchandoColeccion_entry.coleccion
                coleccion_dict = {
                        "id": coleccion.id,
                        "orden": coleccion.orden,
                        "index": coleccion.index,                      
                        "modo": estaEscuchandoColeccion_entry.modo
                    }
            else: 
                coleccion_dict = None

        else: 
            cancion_dict = None
            coleccion_dict = None
        
    return jsonify({"cancion": cancion_dict, "coleccion": coleccion_dict}), 200


"""Cambia el estado de la cancion actual"""
@song_bp.route("/play-pause", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
@sid_required()
def play_pause():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    sid = request.headers.get("sid")
    correo = get_jwt_identity()
    reproduciendo = data.get("reproduciendo")
    progreso = data.get("progreso")

    if reproduciendo is None or (not reproduciendo and progreso is None):
        return jsonify({"error": "Faltan campos en la peticion."}), 400 
    
    with get_db() as db:
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)
        if not estaEscuchandoCancion_entry:
            return jsonify({"error": "El usuario no esta reproduciendo ninguna cancion."}), 404 

        estaEscuchandoCancion_entry.reproduciendo = reproduciendo
        if not reproduciendo:
            estaEscuchandoCancion_entry.progreso = progreso
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    # Emitir el evento de socket con el nuevo estado de la cancion
    socketio.emit("play-pause-ws", {"reproduciendo": reproduciendo, "progreso": progreso if not reproduciendo else None}, room=correo, skip_sid=sid)

    return jsonify(""), 200


"""Actualiza el progreso de la cancion actual"""
@song_bp.route("/change-progreso", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
@sid_required()
def change_progreso():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    sid = request.headers.get("sid")
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
    
    # Emitir el evento de socket con el nuevo progreso
    socketio.emit("change-progreso-ws", {"progreso": progreso}, room=correo, skip_sid=sid)

    return jsonify(""), 200


"""Cambia el modo de reproduccion de la cancion actual"""
@song_bp.route("/change-modo", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
@sid_required()
def change_modo():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    sid = request.headers.get("sid")
    correo = get_jwt_identity()
    modo = data.get("modo")
    if not modo:
        return jsonify({"error": "Falta el modo de la cancion."}), 400 
    
    if modo not in ["aleatorio", "enBucle", "enOrden"]:
        return jsonify({"error": "Modo incorrecto."}), 400 

    with get_db() as db:
        estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)
        if not estaEscuchandoColeccion_entry:
            return jsonify({"error": "El usuario no esta reproduciendo ninguna cancion en una coleccion."}), 404 

        estaEscuchandoColeccion_entry.modo = modo    
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    # Emitir el evento de socket con el nuevo modo
    socketio.emit("change-modo-ws", {"modo": modo}, room=correo, skip_sid=sid)

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
            # Si esta en favoritos y fav == False, eliminarla
            db.delete(fav_entry)

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
def add_reproduction():
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
@sid_required()
def put_cancion_sola():    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    sid = request.headers.get("sid")
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
                                                                progreso=0, reproduciendo=True)
            db.add(estaEscuchandoCancion_entry)
        
        # Actualizar cancion actual
        else:
            estaEscuchandoCancion_entry.Cancion_id = cancion_id
            estaEscuchandoCancion_entry.progreso = 0
            estaEscuchandoCancion_entry.reproduciendo = True
        
            # Recuperar coleccion actual
            estaEscuchandoColeccion_entry = db.get(EstaEscuchandoColeccion, correo)

            # Quitar coleccion actual
            if estaEscuchandoColeccion_entry:
                db.delete(estaEscuchandoColeccion_entry)
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

        cancion = estaEscuchandoCancion_entry.cancion
        # Emitir evento de socket con la nueva cancion actual
        socketio.emit("put-cancion-sola-ws", {"cancion": {
                                                "id": cancion_id,
                                                "audio": cancion.audio,
                                                "nombre": cancion.nombre,
                                                "nombreArtisticoArtista": cancion.artista.nombreArtistico,
                                                "nombreUsuarioArtista": cancion.artista.nombreUsuario,
                                                "progreso": 0,
                                                "fav": fav(cancion.id, correo, db),
                                                "fotoPortada": cancion.album.fotoPortada}}, room=correo, skip_sid=sid)
        
        return jsonify({ "audio": estaEscuchandoCancion_entry.cancion.audio,
                "nombreUsuarioArtista": estaEscuchandoCancion_entry.cancion.artista.nombreUsuario,
                "fav": fav(cancion_id, correo, db)}), 200

"""Reproduce una cancion en una coleccion"""
@song_bp.route("/put-cancion-coleccion", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
@sid_required()
def put_cancion_coleccion():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    sid = request.headers.get("sid")
    correo = get_jwt_identity()
    coleccion_id = data.get("coleccion")
    modo = data.get("modo")
    orden = data.get("orden")
    index = data.get("index")
    if not coleccion_id or not modo or not orden or not index:
        return jsonify({"error": "Faltan campos en la peticion."}), 400 

    if modo not in ["enBucle", "aleatorio", "enOrden"]:
        return jsonify({"error": "Modo no valido."}), 400 

    if index > len(orden):
        return jsonify({"error": "Index no valido."}), 400 

    cancion_id = orden[index - 1]
    with get_db() as db:
        # Recuperar cancion actual
        estaEscuchandoCancion_entry = db.get(EstaEscuchandoCancion, correo)

        # 1ª cancion actual
        if not estaEscuchandoCancion_entry:
            estaEscuchandoCancion_entry = EstaEscuchandoCancion(Oyente_correo=correo, Cancion_id=cancion_id, 
                                                                progreso=0, reproduciendo=True)
            db.add(estaEscuchandoCancion_entry)
        
        # Actualizar cancion actual
        else:
            estaEscuchandoCancion_entry.Cancion_id = cancion_id
            estaEscuchandoCancion_entry.progreso = 0
            estaEscuchandoCancion_entry.reproduciendo = True

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

        cancion = estaEscuchandoCancion_entry.cancion
        coleccion = estaEscuchandoColeccion_entry.coleccion
        # Emitir evento de socket con la nueva cancion actual
        socketio.emit("put-cancion-sola-ws", {"cancion": {
                                                "id": cancion_id,
                                                "audio": cancion.audio,
                                                "nombre": cancion.nombre,
                                                "nombreArtisticoArtista": cancion.artista.nombreArtistico,
                                                "nombreUsuarioArtista": cancion.artista.nombreUsuario,
                                                "progreso": 0,
                                                "fav": fav(cancion.id, correo, db),
                                                "fotoPortada": cancion.album.fotoPortada},
                                           "coleccion": {
                                                "id": coleccion.id,
                                                "orden": coleccion.orden,
                                                "index": coleccion.index,                      
                                                "modo": estaEscuchandoColeccion_entry.modo}}, room=correo, skip_sid=sid)

        return jsonify({"audio": estaEscuchandoCancion_entry.cancion.audio,
                "nombreUsuarioArtista": estaEscuchandoCancion_entry.cancion.artista.nombreUsuario,
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
    
    artista = data.get("artista")
    nombre = data.get("nombre")
    duracion = data.get("duracion")
    audio_url = data.get("audio_url")
    album_id = data.get("album_id")
    tags = data.get("tags")

    if not nombre or not artista or not album_id or not duracion or not audio_url or not tags:
        return jsonify({
        "error": "Faltan datos de la canción.",
        "nombre": nombre,
        "artista": artista,
        "album_id": album_id,
        "duracion": duracion,
        "audio_url": audio_url,
        "tags": tags
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

    try:

        # Guardar la información de la canción en la base de datos
        with get_db() as db:
            nueva_cancion = Cancion(
                Artista_correo=artista,
                nombre=nombre,
                duracion=duracion,
                audio=audio_url,
                fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                reproducciones=0,
                Album_id=album_id,
                puesto=obtener_ultimo_puesto(db, album_id, artista) + 1
            )

            db.add(nueva_cancion)

            # Añadir los tags
            for tag in tags:
                genero = db.get(GeneroMusical, tag)
                nueva_cancion.generosMusicales.append(genero)

            db.commit()

        return jsonify({"message": "Canción subida exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": f"Error al subir la canción: {e}"}), 500   

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
            public_id = audio_url.split('/')[-1].split('.')[0]

            # Borrar la canción de la base de datos
            db.delete(cancion)

            try:
                cloudinary.uploader.destroy(public_id, resource_type="video")
            except Exception as e:
                return f"Error al eliminar la canción de Cloudinary: {e}"

            db.commit()

        return jsonify({"message": "Canción borrada exitosamente."}), 200

    except Exception as e:
        return jsonify({"error": f"Error al borrar la canción: {e}"}), 500

