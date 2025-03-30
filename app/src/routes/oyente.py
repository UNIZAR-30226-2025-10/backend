from sqlalchemy import select
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
from utils.hash import hash, verify
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

"""Devuelve informacion de un oyente mediante su nombreUsuario"""
@oyente_bp.route("/get-datos-oyente", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista", "oyente")
def get_datos_oyente():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del usuario."}), 400
    
    correo_actual = get_jwt_identity()
    
    with get_db() as db:
        oyente = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404
        
        usuario_actual = db.get(Oyente, correo_actual)
        siguiendo = usuario_actual in oyente.seguidores if usuario_actual else False
        
        ultimo_noizzy = db.query(Noizzy).filter_by(Oyente_correo=oyente.correo).order_by(Noizzy.fecha.desc()).first()
        
        return jsonify({
            "oyente": {
                "nombreUsuario": oyente.nombreUsuario,
                "numSeguidos": len(oyente.seguidos),
                "numSeguidores": len(oyente.seguidores),
                "siguiendo": siguiendo,
                "fotoPerfil": oyente.fotoPerfil
            },
            "ultimoNoizzy": {
                "texto": ultimo_noizzy.texto if ultimo_noizzy else None,
                "id": ultimo_noizzy.id if ultimo_noizzy else None,
                "fecha": ultimo_noizzy.fecha.strftime("%d/%m/%Y %H:%M") if ultimo_noizzy else None,
                "like": usuario_actual in ultimo_noizzy.likes if ultimo_noizzy and usuario_actual else False
            } if ultimo_noizzy else None
        }), 200
    

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
            "numSeguidores": len(oyente.seguidores),
            "fotoPerfil": oyente.fotoPerfil  
            }), 200


"""Devuelve una lista con los seguidos del usuario logueado"""
@oyente_bp.route('/get-mis-seguidos', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_mis_seguidos():
    correo = get_jwt_identity()  

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        seguidos = [
            {
                "nombreUsuario": s.nombreUsuario,
                "fotoPerfil": s.fotoPerfil,
                "tipo": s.tipo
            }
            for s in oyente_entry.seguidos[:30]
        ]

    return jsonify({"seguidos": seguidos}), 200


"""Devuelve una lista con los seguidores del usuario logueado"""
@oyente_bp.route('/get-mis-seguidores', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_mis_seguidores():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        seguidores = [
            {
                "nombreUsuario": s.nombreUsuario,
                "fotoPerfil": s.fotoPerfil,
                "tipo": s.tipo
            }
            for s in oyente_entry.seguidores[:30]
        ]

    return jsonify({"seguidores": seguidores}), 200


"""Devuelve una lista con los seguidos del usuario con nombre dado"""
@oyente_bp.route('/get-seguidos', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_seguidos():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del usuario."}), 400
    
    with get_db() as db:
        oyente = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404

        seguidos = [
            {
                "nombreUsuario": s.nombreUsuario,
                "fotoPerfil": s.fotoPerfil,
                "tipo": s.tipo
            }
            for s in oyente.seguidos[:30]
        ]

    return jsonify({"seguidos": seguidos}), 200


"""Devuelve una lista con los seguidores del usuario con nombre dado"""
@oyente_bp.route('/get-seguidores', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_seguidores():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del usuario."}), 400
    
    with get_db() as db:
        oyente = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404

        seguidores = [
            {
                "nombreUsuario": s.nombreUsuario,
                "fotoPerfil": s.fotoPerfil,
                "tipo": s.tipo
            }
            for s in oyente.seguidores[:30]
        ]

    return jsonify({"seguidores": seguidores}), 200


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
        artistas_unicos = set()
        artistas = []

        for h in oyente_entry.historialCancion[:30]:
            clave = (h.cancion.artista.nombreUsuario)
            if clave not in artistas_unicos:
                artistas_unicos.add(clave)
                artistas.append({
                    "nombreUsuario": h.cancion.artista.nombreUsuario,
                    "nombreArtistico": h.cancion.artista.nombreArtistico,
                    "fotoPerfil": h.cancion.artista.fotoPerfil
                })
    
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


"""Devuelve una lista con las playlists del usuario logueado"""
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

        participando_playlists = [
            {
                "id": s.id,
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in oyente_entry.participante[:30]
        ]

        playlists = mis_playlists + participando_playlists

        playlists_ordenadas = sorted(playlists, key=lambda x: x["nombre"])
        
    return jsonify({"playlists": playlists_ordenadas[:30]}), 200


"""Devuelve una lista con las playlists públicas del usuario dado un nombreUsuario"""
@oyente_bp.route('/get-playlists', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_playlists():
    nombre_usuario = request.args.get("nombreUsuario")
    if not nombre_usuario:
        return jsonify({"error": "Falta el nombreUsuario del usuario."}), 400
    
    with get_db() as db:
        oyente = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 401

        stmt_mis_playlists = select(Playlist).where(
            Playlist.Oyente_correo == oyente.correo,
            Playlist.privacidad == False
        ).limit(30)
        mis_playlists = [
            {
                "id": s.id,
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in db.execute(stmt_mis_playlists).scalars().all()
        ]

        stmt_participando_playlists = select(Playlist).join(Playlist.participantes).where(
            Oyente.correo == oyente.correo,
            Playlist.privacidad == False
        ).limit(30)
        participando_playlists = [
            {
                "id": s.id,
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in db.execute(stmt_participando_playlists).scalars().all()
        ]

        playlists = mis_playlists + participando_playlists

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

    return jsonify(""), 200


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

    if not foto_perfil or not nombre_usuario:
        return jsonify({"error": "Faltan datos para actualizar el oyente."}), 400

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "El oyente no existe."}), 404

        if foto_perfil != oyente_entry.fotoPerfil:

            fotoAntigua = oyente_entry.fotoPerfil
            public_id = fotoAntigua.split('/')[-2] + '/' + fotoAntigua.split('/')[-1].split('.')[0]
            print(public_id)

            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception as e:
                return f"Error al eliminar el album de Cloudinary: {e}"
            
            oyente_entry.fotoPerfil = foto_perfil
            
        if nombre_usuario != oyente_entry.nombreUsuario:
            # Verificar si el nombre de usuario ya existe
            existing_user = db.query(Oyente).filter_by(nombreUsuario=nombre_usuario).first()
            if existing_user:
                return jsonify({"error": "El nombre de usuario ya está en uso."}), 400
            oyente_entry.nombreUsuario = nombre_usuario

        db.commit()

    return jsonify({"message": "Datos del oyente actualizados exitosamente."}), 200


"""Actualiza la contraseña de un usuario"""
@oyente_bp.route('/change-contrasenya', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def change_contrasenya():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    contrasenya_actual = data.get('contrasenya')
    nueva_contrasenya = data.get('nueva')

    if not contrasenya_actual or not nueva_contrasenya:
        return jsonify({"error": "Faltan datos para actualizar la contraseña."}), 400

    with get_db() as db:
        usuario = db.get(Usuario, correo)
        if not usuario:
            return jsonify({"error": "El usuario no existe."}), 404

        # Verificar la contraseña actual
        if not verify(contrasenya_actual, usuario.contrasenya):
            return jsonify({"error": "La contraseña actual es incorrecta."}), 401

        # Actualizar la contraseña
        usuario.contrasenya = hash(nueva_contrasenya)
        db.commit()

    return jsonify(""), 200


"""Actualiza la contraseña de un usuario"""
@oyente_bp.route('/change-follow', methods=['PUT'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def change_follow():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    siguiendo = data.get("siguiendo")
    nombreUsuario = data.get("nombreUsuario")
    if not nombreUsuario or siguiendo is None:
        return jsonify({"error": "Faltan campos en la peticion."}), 400
    
    with get_db() as db:
        oyente = db.query(Oyente).filter_by(nombreUsuario=nombreUsuario).first()
        if not oyente:
            return jsonify({"error": "El oyente no existe."}), 404
        
        usuario_actual = db.get(Oyente, correo)
        siguiendo_entry = usuario_actual in oyente.seguidores if usuario_actual else False
        
        if siguiendo and not siguiendo_entry:
            # Si no lo sigo y siguiendo == True, seguirlo
            usuario_actual.seguidos.append(oyente)

        elif not siguiendo and siguiendo_entry:
            # Si lo sigo y siguiendo == False, dejar de seguirlo
            usuario_actual.seguidos.remove(oyente)

        elif siguiendo_entry:
            return jsonify({"error": "Ya sigues a este usuario."}), 409

        else:
            return jsonify({"error": "No sigues a este usuario."}), 404
        
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 200