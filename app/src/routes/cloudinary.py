
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
import os
import cloudinary
import time

cloudinary_bp = Blueprint('cloudinary', __name__) 

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

"""Devuelve la firma para hacer peticiones a cloudinary"""
@cloudinary_bp.route('/get-signature', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def generate_signed_upload():
    folder = request.args.get("folder")
    if not folder:
        return jsonify({"error": "Faltan datos en la peticion."}), 400
    try:
        # Crear parámetros para firmar la solicitud
        params_to_sign = {
            "timestamp": int(time.time()),  # Usar el módulo time correctamente
            "folder": folder  # Establecer un folder para las cargas
        }

        # Generar la firma usando la API de Cloudinary
        signature = cloudinary.utils.api_sign_request(params_to_sign, cloudinary.config().api_secret)

        # Devolver la respuesta en formato JSON
        return jsonify({
            "signature": signature,
            "api_key": cloudinary.config().api_key,
            "timestamp": params_to_sign["timestamp"],
            "cloud_name": cloudinary.config().cloud_name
        }), 200

    except Exception as e:
        # En caso de error, devolver un mensaje de error
        return jsonify({"error": str(e)}), 500