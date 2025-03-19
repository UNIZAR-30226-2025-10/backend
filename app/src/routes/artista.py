from utils.decorators import roles_required, tokenVersion_required
from db.models import Oyente, Artista, Album
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify

artista_bp = Blueprint('info', __name__) 

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