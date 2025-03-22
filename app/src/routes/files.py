import pytz
import os
import cloudinary.uploader
from flask import Blueprint, request, jsonify
from db.models import *
from db.db import get_db
from utils.decorators import roles_required, tokenVersion_required
from flask_jwt_extended import jwt_required



#############################################################
## CONF ##
##########

files_bp = Blueprint('files', __name__)

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

#############################################################    
## GET ##
#########

"""Devuelve informacion de una cancion"""
@files_bp.route("/get-cancion", methods=["GET"])
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
            "artista":cancion.Artista_correo,
            "audio": cancion.audio,
            "fotoPortada": cancion.album.fotoPortada
            }), 200

@files_bp.route('/get-tags', methods=['GET'])
def get_tags():
    try:
        with get_db() as session:
            tags = session.query(GeneroMusical).all()
            return jsonify([tag.nombre for tag in tags]), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener los tags: {e}"}), 500

