
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
import os
import cloudinary

cloudinary_bp = Blueprint('cloudinary', __name__) 

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

"""Devuelve las credenciales de Cloudinary"""
@cloudinary_bp.route('/get-cloudinary-credentials', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_cloudinary_credentials():
    credentials = {
        "cloud_name": cloudinary.config().cloud_name,
        "api_key": cloudinary.config().api_key,
        "api_secret": cloudinary.config().api_secret,
    }
    return jsonify(credentials), 200