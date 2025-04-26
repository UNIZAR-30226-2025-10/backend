from utils.decorators import roles_required, tokenVersion_required
from db.models import Oyente, Artista, Cancion, Playlist, EsParteDePlaylist, Album, featuring_table, Sigue
from db.db import get_db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify
from sqlalchemy import select, and_, func, exists
from sqlalchemy.orm import aliased
import cloudinary.uploader
import os

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
        subq_seguidores = (
            select(func.count())
            .select_from(Sigue)
            .where(Sigue.Seguido_correo == Artista.correo)
            .scalar_subquery()
        )

        subq_seguidos = (
            select(func.count())
            .select_from(Sigue)
            .where(Sigue.Seguidor_correo == Artista.correo)
            .scalar_subquery()
        )

        stmt_artista = (
            select(
                Artista,
                subq_seguidores.label("num_seguidores"),
                subq_seguidos.label("num_seguidos")
            )
            .where(Artista.nombreUsuario == nombre_usuario)
        )

        artista_result = db.execute(stmt_artista).one_or_none()
        if not artista_result:
            return jsonify({"error": "El artista no existe."}), 404

        artista, num_seguidores, num_seguidos = artista_result
        
        stmt = select(exists(select(Sigue).where(and_(Sigue.Seguidor_correo == correo_actual, Sigue.Seguido_correo == artista.correo))))
        siguiendo = db.execute(stmt).scalar_one()

        return jsonify({"artista": {"nombreUsuario": artista.nombreUsuario,
                                    "nombreArtistico": artista.nombreArtistico,
                                    "biografia": artista.biografia,
                                    "numSeguidos": num_seguidos,
                                    "numSeguidores": num_seguidores,
                                    "siguiendo": siguiendo,
                                    "fotoPerfil": artista.fotoPerfil}}), 200
    

"""Devuelve informacion del artista logueado"""
@artista_bp.route("/get-mis-datos-artista", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_mis_datos_artista():
    correo = get_jwt_identity()
    
    with get_db() as db:
        subq_seguidores = (
            select(func.count())
            .select_from(Sigue)
            .where(Sigue.Seguido_correo == Artista.correo)
            .scalar_subquery()
        )

        subq_seguidos = (
            select(func.count())
            .select_from(Sigue)
            .where(Sigue.Seguidor_correo == Artista.correo)
            .scalar_subquery()
        )

        stmt_artista = (
            select(
                Artista,
                subq_seguidores.label("num_seguidores"),
                subq_seguidos.label("num_seguidos")
            )
            .where(Artista.correo == correo)
        )

        artista_result = db.execute(stmt_artista).one_or_none()
        if not artista_result:
            return jsonify({"error": "El artista no existe."}), 404

        artista, num_seguidores, num_seguidos = artista_result
        
        return jsonify({
            "nombre":artista.nombreUsuario,
            "nombreArtistico":artista.nombreArtistico,
            "numSeguidos": num_seguidos, 
            "numSeguidores": num_seguidores,
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
    limite = request.args.get("limite")
    limite = int(limite) if limite else None

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
                for cancion in (artista.canciones[:limite] if limite else artista.canciones)
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
    limite = request.args.get("limite")
    limite = int(limite) if limite else None

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
                for cancion in (artista.canciones[:limite] if limite else artista.canciones)
            ]
    
    return jsonify({"canciones": canciones}), 200


"""Devuelve una lista con las canciones que el usuario logueado tiene favoritos
   de un artista concreto"""
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

        id_fav = db.execute(select(Playlist.id).where(and_(Playlist.nombre == "Favoritos", Playlist.Oyente_correo == correo_actual))).scalar()

        stmt_canciones = select(Cancion.id, Cancion.nombre, Cancion.duracion, Album.nombre.label("album"),
            Album.fotoPortada, EsParteDePlaylist.fecha
            ).join(EsParteDePlaylist, EsParteDePlaylist.Cancion_id == Cancion.id
            ).join(Album, Album.id == Cancion.Album_id
            ).where(and_(
                Cancion.Artista_correo == artista.correo,
                EsParteDePlaylist.Playlist_id == id_fav))

        resultados = db.execute(stmt_canciones).fetchall()

        canciones = []
        for resultado in resultados:
            stmt = (
                select(Artista.nombreArtistico)
                .join(featuring_table, Artista.correo == featuring_table.c.Artista_correo)
                .where(featuring_table.c.Cancion_id == resultado[0])
            )
    
            featuring = [row[0] for row in db.execute(stmt).all()]
            canciones.append(
                {
                    "id": resultado[0],
                    "nombre": resultado[1],
                    "fotoPortada": resultado[4],
                    "album": resultado[3],
                    "duracion": resultado[2],
                    "featuring": featuring,
                    "fecha": resultado[5].strftime("%d %m %Y")
                }
            )
    
    return jsonify({"canciones_favoritas": canciones}), 200


"""Devuelve cuantas canciones favoritas tiene el usuario logueado de un artista"""
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
        
        stmt = (
            select(func.count(Cancion.id))
            .join(EsParteDePlaylist, Cancion.id == EsParteDePlaylist.Cancion_id)
            .join(Playlist, EsParteDePlaylist.Playlist_id == Playlist.id)
            .where(
                Cancion.Artista_correo == artista.correo,
                Playlist.nombre == "Favoritos",
                Playlist.Oyente_correo == correo_actual
            )
        )

        total_favoritas = db.execute(stmt).scalar()
    
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

        stmt_fav = select(EsParteDePlaylist.Cancion_id).join(Playlist
            ).where(and_(
                Playlist.nombre == "Favoritos",
                Playlist.Oyente_correo == correo
            )
        )
        favoritos_set = {row[0] for row in db.execute(stmt_fav).all()}

        canciones = [
                {
                    "id": cancion.id,
                    "nombre": cancion.nombre,
                    "reproducciones": cancion.reproducciones,
                    "featuring": [f.nombreArtistico for f in cancion.featuring],
                    "duracion": cancion.duracion,
                    "fav": cancion.id in favoritos_set,
                    "fotoPortada": cancion.album.fotoPortada
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
    limite = request.args.get("limite")
    limite = int(limite) if limite else None
    
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
            for album in (artista.albumes[:limite] if limite else artista.albumes)
        ]
    
    return jsonify({"albumes": albumes}), 200


"""Devuelve una lista con los álbumes del artista logueado"""
@artista_bp.route('/get-mis-albumes', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_mis_albumes():
    correo = get_jwt_identity()
    limite = request.args.get("limite")
    limite = int(limite) if limite else None

    with get_db() as db:
        artista_entry = db.get(Artista, correo)
        if not artista_entry:
            return jsonify({"error": "El artista no existe."}), 404

        albumes = [
            {
                "id" : album.id,
                "nombre": album.nombre,
                "fotoPortada": album.fotoPortada
            }
            for album in (artista_entry.albumes[:limite] if limite else artista_entry.albumes)
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

            if artista_entry.fotoPerfil != "DEFAULT":
                foto_antigua = artista_entry.fotoPerfil
                public_id = foto_antigua.split('/')[-2] + '/' + foto_antigua.split('/')[-1].split('.')[0]

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
