from utils.decorators import roles_required, tokenVersion_required
from db.models import Oyente, Artista, Album
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify

info_bp = Blueprint('info', __name__) 


"""Devuelve informacion de un oyente"""
@info_bp.route("/get-mis-datos-oyente", methods=["GET"])
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
            "nombre": oyente.nombreUsuario,
            "seguidos_count": len(oyente.seguidos),  
            "seguidores_count": len(oyente.seguidores)  
            }), 200
    
"""Devuelve informacion de un artista"""
@info_bp.route("/get-mis-datos-artista", methods=["GET"])
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
            "seguidos_count": len(artista.seguidos), 
            "seguidores_count": len(artista.seguidores) 
            }), 200
    
"""Devuelve informacion de un album"""
@info_bp.route("/get-datos-album", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_datos_album():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:     
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 401
        canciones = [
            {
                "id": cancion.id,
                "fotoPortada": album.fotoPortada,
                "nombre": cancion.nombre,
                "duracion": cancion.duracion,
                "fechaPublicacion": cancion.fechaPublicacion.isoformat(),
                "puesto": cancion.puesto
            }
            for cancion in album.canciones
        ]

        return jsonify({
            "nombre": album.nombre,
            "fotoPortada": album.fotoPortada,
            "nombreArtisticoArtista": album.artista.nombreArtistico, 
            "fechaPublicacion": album.fechaPublicacion.isoformat(),
            "duracion": sum(cancion.duracion for cancion in album.canciones),
            "canciones": canciones
            }), 200

"""Devuelve una lista con los álbumes de un artista"""
@info_bp.route('/get-mis-albumes', methods=['GET'])
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