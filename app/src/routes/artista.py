from utils.decorators import roles_required, tokenVersion_required
from db.models import Oyente, Artista, Noizzy, Cancion
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify
import cloudinary.uploader
import os
from utils.fav import fav

artista_bp = Blueprint('info', __name__) 

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

"""Devuelve informacion de un artista mediante su nombreUsuario"""
@artista_bp.route("/get-datos-artista", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_datos_artista():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    correo_actual = get_jwt_identity()
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404
        
        usuario_actual = db.get(Oyente, correo_actual)
        siguiendo = usuario_actual in artista.seguidores if usuario_actual else False
        
        ultimo_noizzy = db.query(Noizzy).filter_by(Oyente_correo=artista.correo).order_by(Noizzy.fecha.desc()).first()
        
        return jsonify({
            "artista": {
                "nombreUsuario": artista.nombreUsuario,
                "nombreArtistico": artista.nombreArtistico,
                "biografia": artista.biografia,
                "numSeguidos": len(artista.seguidos),
                "numSeguidores": len(artista.seguidores),
                "siguiendo": siguiendo,
                "fotoPerfil": artista.fotoPerfil
            },
            "ultimoNoizzy": {
                "texto": ultimo_noizzy.texto if ultimo_noizzy else None,
                "id": ultimo_noizzy.id if ultimo_noizzy else None,
                "fecha": ultimo_noizzy.fecha.strftime("%d/%m/%Y %H:%M") if ultimo_noizzy else None,
                "like": usuario_actual in ultimo_noizzy.likes if ultimo_noizzy and usuario_actual else False
            } if ultimo_noizzy else None
        }), 200
    

"""Devuelve informacion del artista logueado"""
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
            "biografia" : artista.biografia,
            "fotoPerfil": artista.fotoPerfil
            }), 200
    

"""Devuelve una lista con las canciones del artista logueado"""
@artista_bp.route('/get-mis-canciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_mis_canciones():
    correo = get_jwt_identity()
    
    with get_db() as db:
        artista = db.get(Artista, correo)
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404

        canciones = [
                {
                    "id": cancion.id,
                    "nombre": cancion.nombre,
                    "fotoPortada": cancion.album.fotoPortada if cancion.album else None
                }
                for cancion in artista.canciones
            ]
    
    return jsonify({"canciones": canciones}), 200


"""Devuelve una lista con las canciones de un artista"""
@artista_bp.route('/get-canciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_canciones():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404

        canciones = [
                {
                    "id": cancion.id,
                    "nombre": cancion.nombre,
                    "fotoPortada": cancion.album.fotoPortada if cancion.album else None
                }
                for cancion in artista.canciones
            ]
    
    return jsonify({"canciones": canciones}), 200


"""Devuelve una lista con las canciones de un artista"""
@artista_bp.route('/get-canciones-favoritas', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_canciones_favoritas():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    correo_actual = get_jwt_identity()
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404

        canciones = [
            {
                "id": cancion.id,
                "nombre": cancion.nombre,
                "fotoPortada": cancion.album.fotoPortada if cancion.album else None
            }
            for cancion in artista.canciones
            if fav(cancion.id, correo_actual, db)
        ]
    
    return jsonify({"canciones_favoritas": canciones}), 200


"""Devuelve cuantas canciones favoritas tiene el user de un artista"""
@artista_bp.route('/get-numero-canciones-favoritas', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_numero_canciones_favoritas():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    correo_actual = get_jwt_identity()
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404

        total_favoritas = sum(1 for cancion in artista.canciones if fav(cancion.id, correo_actual, db))
    
    return jsonify({"total_favoritas": total_favoritas}), 200


"""Devuelve una lista con las 5 canciones más populares de un artista"""
@artista_bp.route('/get-canciones-populares', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_canciones_populares():
    correo = get_jwt_identity()
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404
        
        canciones_populares = (
            db.query(Cancion)
            .filter(Cancion.Artista_correo == artista.correo)
            .order_by(Cancion.reproducciones.desc())
            .limit(5)
            .all()
        )

        canciones = [
                {
                    "id": cancion.id,
                    "nombre": cancion.nombre,
                    "reproducciones": cancion.reproducciones,
                    "duracion": cancion.duracion,
                    "fav": fav(cancion.id, correo, db),
                    "fotoPortada": cancion.album.fotoPortada if cancion.album else None
                }
                for cancion in canciones_populares
            ]
    
    return jsonify({"canciones_populares": canciones}), 200


"""Devuelve una lista con los álbumes de un artista"""
@artista_bp.route('/get-albumes', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_albumes():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del artista."}), 400
    
    with get_db() as db:
        artista = db.query(Artista).filter_by(nombreUsuario=nombre_usuario).first()
        if not artista:
            return jsonify({"error": "El artista no existe."}), 404

        albumes = [
            {
                "id" : album.id,
                "nombre": album.nombre,
                "fotoPortada": album.fotoPortada
            }
            for album in artista.albumes[:30]
        ]
    
    return jsonify({"albumes": albumes}), 200


"""Devuelve una lista con los álbumes del artista logueado"""
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
    biografia = data.get('biografia')

    if not foto_perfil or not nombre_usuario or not nombre_artistico or not biografia:
        return jsonify({"error": "Faltan datos para actualizar el artista."}), 400

    with get_db() as db:
        artista_entry = db.get(Artista, correo)
        if not artista_entry:
            return jsonify({"error": "El artista no existe."}), 404

        if foto_perfil != artista_entry.fotoPerfil:
            foto_antigua = artista_entry.fotoPerfil
            public_id = foto_antigua.split('/')[-1].split('.')[0]

            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception as e:
                return jsonify({"error": f"Error al eliminar la foto de perfil antigua de Cloudinary: {e}"}), 500

            artista_entry.fotoPerfil = foto_perfil

        if nombre_usuario != artista_entry.nombreUsuario:
            # Verificar si el nombre de usuario ya existe
            existing_user = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
            if existing_user:
                return jsonify({"error": "El nombre de usuario ya está en uso."}), 400
            artista_entry.nombreUsuario = nombre_usuario

        if nombre_artistico != artista_entry.nombreArtistico:
            artista_entry.nombreArtistico = nombre_artistico

        if biografia != artista_entry.biografia:
            artista_entry.biografia = biografia

        db.commit()

    return jsonify({"message": "Datos del artista actualizados exitosamente."}), 200
