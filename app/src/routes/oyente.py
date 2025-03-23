from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
from utils.recommendation import obtener_recomendaciones
import cloudinary.uploader
import os

oyente_bp = Blueprint('oyente', __name__)


cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)



"""Devuelve informacion de un oyente"""
@oyente_bp.route("/get-mis-datos-oyente", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente")
def get_mis_datos_oyente():
    correo = get_jwt_identity()
    
    with get_db() as db:
        oyente = db.get(Oyente, correo)
        if not oyente:
            return jsonify({"error": "El oyente no existe"}), 401
        
        return jsonify({
            "nombreUsuario": oyente.nombreUsuario,
            "numSeguidos": len(oyente.seguidos),  
            "numSeguidores": len(oyente.seguidores)  
            }), 200


"""Devuelve una lista con los seguidos del usuario"""
@oyente_bp.route('/get-seguidos', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_seguidos():
    correo = get_jwt_identity()  

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        seguidos = [
            {
                "nombreUsuario": s.nombreUsuario,
                "fotoPerfil": s.fotoPerfil
            }
            for s in oyente_entry.seguidos[:30]
        ]

    return jsonify({"seguidos": seguidos}), 200


"""Devuelve una lista con el historial de artistas del usuario"""
@oyente_bp.route('/get-historial-artistas', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_artistas():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Construir el diccionario con los artistas escuchados
        artistas = [
            {
                "nombreUsuario": h.cancion.artista.nombreUsuario,
                "nombreArtistico" : h.cancion.artista.nombreArtistico,
                "fotoPerfil": h.cancion.artista.fotoPerfil
            }
            for h in oyente_entry.historialCancion[:30]
        ]
    
    return jsonify({"historial_artistas": artistas}), 200


"""Devuelve una lista con el historial de canciones del usuario"""
@oyente_bp.route('/get-historial-canciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_canciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Construir el diccionario con las canciones escuchadas
        historial = [
            {
                "id": h.cancion.id,
                "nombreArtisticoArtista" : h.cancion.artista.nombreArtistico,
                "nombre": h.cancion.nombre,
                "fotoPortada": h.cancion.album.fotoPortada
            }
            for h in oyente_entry.historialCancion[:30]
        ]
    
    return jsonify({"historial_canciones": historial}), 200


"""Devuelve una lista con el historial de albumes y playlists del usuario"""
@oyente_bp.route('/get-historial-colecciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_colecciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        historial = [
            {
                "id": h.coleccion.id,
                "nombre": h.coleccion.nombre,
                "fotoPortada": h.coleccion.fotoPortada,
                "autor": (
                    h.coleccion.oyente.nombreUsuario if isinstance(h.coleccion, Playlist)
                    else h.coleccion.artista.nombreArtistico if isinstance(h.coleccion, Album)
                    else "Desconocido"
                )
            }
            for h in oyente_entry.historialColeccion[:30]
        ]
    
    return jsonify({"historial_colecciones": historial}), 200


"""Devuelve una lista con las playlists del usuario"""
@oyente_bp.route('/get-mis-playlists', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_mis_playlists():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion con playlists creadas
        mis_playlists = [
            {
                "id": s.id,
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in oyente_entry.playlists[:30]
        ]

        # Accede directamente a la relacion con playlists en las que se participa
        participando_playlists = [
            {
                "id": s.id,
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in oyente_entry.participante[:30]
        ]

        # Unimos ambos diccionarios
        playlists = mis_playlists + participando_playlists

        # Ordenamos el diccionario por el campo "nombre"
        playlists_ordenadas = sorted(playlists, key=lambda x: x["nombre"])
        
    return jsonify({"playlists": playlists_ordenadas[:30]}), 200


"""Devuelve una lista con las canciones recomendadas para el usuario"""
@oyente_bp.route('/get-recomendaciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_recomendaciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 400
        
        canciones_recomendadas = obtener_recomendaciones(oyente_entry, db)

    return jsonify({"canciones_recomendadas": canciones_recomendadas}), 200


"""Envia a la BD el volumen cada vez que se modifica"""
@oyente_bp.route('/change-volumen', methods=['PATCH'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def change_volumen():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400
    
    correo = get_jwt_identity()
    volumen = data.get('volumen')
    if volumen is None or not (0 <= volumen <= 100):
        return jsonify({"error": "El volumen debe estar entre 0 y 100."}), 400

    with get_db() as db:
        # Obtener directamente al Oyente desde la tabla 'Oyente'
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "El usuario no es un oyente."}), 404

        # Actualizar el volumen
        oyente_entry.volumen = volumen
        db.commit()

    return jsonify({"message": "Volumen actualizado exitosamente."}), 200


"""Actualiza los datos de un oyente"""
@oyente_bp.route('/change-datos-oyente', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def change_datos_oyente():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    foto_perfil = data.get('fotoPerfil')
    nombre_usuario = data.get('nombre')

    if not foto_perfil and not nombre_usuario:
        return jsonify({"error": "Faltan datos para actualizar el oyente."}), 400

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "El oyente no existe."}), 404

        if foto_perfil:

            fotoAntigua = oyente_entry.fotoPerfil
            public_id = fotoAntigua.split('/')[-1].split('.')[0]
            print(public_id)

            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception as e:
                return f"Error al eliminar el album de Cloudinary: {e}"
            
            oyente_entry.fotoPerfil = foto_perfil
            
        if nombre_usuario:
            # Verificar si el nombre de usuario ya existe
            existing_user = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
            if existing_user:
                return jsonify({"error": "El nombre de usuario ya está en uso."}), 400
            oyente_entry.nombreUsuario = nombre_usuario

        db.commit()

    return jsonify({"message": "Datos del oyente actualizados exitosamente."}), 200