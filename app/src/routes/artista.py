from utils.decorators import roles_required, tokenVersion_required
from db.models import Oyente, Artista, Album
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify
import cloudinary.uploader
import os

artista_bp = Blueprint('info', __name__) 

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)



"""Devuelve informacion de un artista"""
@artista_bp.route("/get-mis-datos-artista", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_mis_datos_artista():
    correo = get_jwt_identity()
    
    with get_db() as db: 
        artista = db.get(Artista, correo)
        if not artista:
            return jsonify({"error": "El artista no existe."}), 401
        
        return jsonify({
            "nombre":artista.nombreUsuario,
            "nombreArtistico":artista.nombreArtistico,
            "numSeguidos": len(artista.seguidos), 
            "numSeguidores": len(artista.seguidores),
            "biografia" : artista.biografia
            }), 200


"""Devuelve una lista con los álbumes de un artista"""
@artista_bp.route('/get-mis-albumes', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_mis_albumes():
    correo = get_jwt_identity()

    with get_db() as db:
        artista_entry = db.get(Artista, correo)
        if not artista_entry:
            return jsonify({"error": "El artista no existe."}), 401

        albumes = [
            {
                "id" : album.id,
                "nombre": album.nombre,
                "fotoPortada": album.fotoPortada
            }
            for album in artista_entry.albumes[:30]
        ]
    
    return jsonify({"albumes": albumes}), 200


"""Actualiza los datos de un artista"""
@artista_bp.route('/change-datos-artista', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def change_datos_artista():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    foto_perfil = data.get('fotoPerfil')
    nombre_usuario = data.get('nombreUsuario')
    nombre_artistico = data.get('nombreArtistico')

    if not foto_perfil and not nombre_usuario and not nombre_artistico:
        return jsonify({"error": "Faltan datos para actualizar el artista."}), 400

    with get_db() as db:
        artista_entry = db.get(Artista, correo)
        if not artista_entry:
            return jsonify({"error": "El artista no existe."}), 404

        if foto_perfil:
            foto_antigua = artista_entry.fotoPerfil
            public_id = foto_antigua.split('/')[-1].split('.')[0]

            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception as e:
                return jsonify({"error": f"Error al eliminar la foto de perfil antigua de Cloudinary: {e}"}), 500

            artista_entry.fotoPerfil = foto_perfil

        if nombre_usuario:
            # Verificar si el nombre de usuario ya existe
            existing_user = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
            if existing_user:
                return jsonify({"error": "El nombre de usuario ya está en uso."}), 400
            artista_entry.nombreUsuario = nombre_usuario

        if nombre_artistico:
            artista_entry.nombreArtistico = nombre_artistico

        db.commit()

    return jsonify({"message": "Datos del artista actualizados exitosamente."}), 200


"""Actualiza la biografía de un artista"""
@artista_bp.route('/change-biografia', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def change_biografia():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    nueva_biografia = data.get('biografia')

    if not nueva_biografia:
        return jsonify({"error": "Falta la biografía para actualizar."}), 400

    with get_db() as db:
        artista_entry = db.get(Artista, correo)
        if not artista_entry:
            return jsonify({"error": "El artista no existe."}), 404

        artista_entry.biografia = nueva_biografia
        db.commit()

    return jsonify({"message": "Biografía actualizada exitosamente."}), 200