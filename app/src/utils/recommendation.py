from db.db import get_db
from db.models import *
from sqlalchemy import select

""" Analiza el historial para encontrar artistas, generos, albumes y playlists mas reproducidos. """
def extraer_caracteristicas(historial_canciones, historial_playlists, db):
    artistas = {}
    generos = {}
    albumes = {}
    playlists = {}

    # Obtener info de las canciones
    for nombre, artista in historial_canciones:
        cancion = db.get(Cancion, (nombre, artista))
        if cancion:
            artistas[cancion.artista] = artistas.get(cancion.artista, 0) + 1
            generos[cancion.genero] = generos.get(cancion.genero, 0) + 1
            albumes[cancion.album] = albumes.get(cancion.album, 0) + 1

    # Obtener playlists reproducidas
    for nombre, creador in historial_playlists:
        playlists[nombre] = playlists.get(nombre, 0) + 1

    return {
        "artistas": artistas,
        "generos": generos,
        "albumes": albumes,
        "playlists": playlists
    }


""" Calcula una puntuacion de recomendacion basada en similitud con el historial. """
def calcular_puntuacion(cancion, caracteristicas):
    puntuacion = 0
    
    if cancion.artista in caracteristicas["artistas"]:
        puntuacion += caracteristicas["artistas"][cancion.artista] * 3  # Artista tiene mas peso
    
    if cancion.genero in caracteristicas["generos"]:
        puntuacion += caracteristicas["generos"][cancion.genero] * 2  # Genero es importante
    
    if cancion.album in caracteristicas["albumes"]:
        puntuacion += caracteristicas["albumes"][cancion.album] * 1.5  # Album tiene peso medio
    
    for playlist in cancion.playlists:
        if playlist in caracteristicas["playlists"]:
            puntuacion += caracteristicas["playlists"][playlist]  # Playlists tienen peso bajo
    
    return puntuacion

def obtener_recomendaciones(usuario, db):
    """ Devuelve 30 canciones recomendadas para el usuario basado en su historial. """
    # Obtener historial del usuario
    historial_canciones = usuario.historialCancion
    historial_playlists = usuario.historialPlaylist

    # Extraer caracteristicas de sus gustos
    caracteristicas = extraer_caracteristicas(historial_canciones, historial_playlists, db)

    # Obtener todas las canciones disponibles en la plataforma
    canciones_disponibles = db.execute(select(Cancion)).scalars().all()

    # Calcular puntuaciones para cada cancion candidata
    canciones_recomendadas = [
        (cancion, calcular_puntuacion(cancion, caracteristicas)) 
        for cancion in canciones_disponibles
        if (cancion.nombre, cancion.Artista_correo) not in historial_canciones  # Evitar repetir canciones ya escuchadas
    ]

    # Ordenar por puntuacion de mayor a menor y tomar las 30 mejores
    canciones_recomendadas.sort(key=lambda x: x[1], reverse=True)

    return [cancion.to_dict() for cancion, _ in canciones_recomendadas[:30]]
