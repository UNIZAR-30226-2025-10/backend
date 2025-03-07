from db.models import *
from sqlalchemy import select

""" Analiza el historial para encontrar artistas, generos, albumes y playlists mas reproducidos. """
def extraer_caracteristicas(historial_canciones, historial_colecciones, db):
    artistas = {}
    generos = {}
    albumes = {}
    playlists = {}

    # Obtener info de las canciones
    for historial in historial_canciones:
        cancion = historial.cancion
        if cancion:
            artistas[cancion.artista.correo] = artistas.get(cancion.artista.correo, 0) + 1
            for genero in cancion.generosMusicales:
                generos[genero.nombre] = generos.get(genero.nombre, 0) + 1
            albumes[cancion.album.id] = albumes.get(cancion.album.id, 0) + 1

    # Obtener colecciones reproducidas (álbumes y playlists)
    for historial in historial_colecciones:
        coleccion = historial.coleccion
        if coleccion.tipo == 'playlist':
            playlists[coleccion.id] = playlists.get(coleccion.id, 0) + 1
        elif coleccion.tipo == 'album':
            albumes[coleccion.id] = albumes.get(coleccion.id, 0) + 1

    return {
        "artistas": artistas,
        "generos": generos,
        "albumes": albumes,
        "playlists": playlists
    }

""" Calcula una puntuacion de recomendacion basada en similitud con el historial. """
def calcular_puntuacion(cancion, caracteristicas):
    puntuacion = 0
    
    if cancion.artista.correo in caracteristicas["artistas"]:
        puntuacion += caracteristicas["artistas"][cancion.artista.correo] * 3  # Artista tiene más peso
    
    for genero in cancion.generosMusicales:
        if genero.nombre in caracteristicas["generos"]:
            puntuacion += caracteristicas["generos"][genero.nombre] * 2  # Género es importante
    
    if cancion.album.id in caracteristicas["albumes"]:
        puntuacion += caracteristicas["albumes"][cancion.album.id] * 1.5  # Álbum tiene peso medio
    
    for playlist in cancion.esParteDePlaylist:
        if playlist.playlist.id in caracteristicas["playlists"]:
            puntuacion += caracteristicas["playlists"][playlist.playlist.id]  # Playlists tienen peso bajo
    
    return puntuacion

""" Devuelve 30 canciones recomendadas para el usuario basado en su historial. """
def obtener_recomendaciones(usuario, db):
    # Obtener historial del usuario
    historial_canciones = usuario.historialCancion
    historial_colecciones = usuario.historialColeccion

    # Extraer características de sus gustos
    caracteristicas = extraer_caracteristicas(historial_canciones, historial_colecciones, db)

    # Obtener todas las canciones disponibles en la plataforma
    canciones_disponibles = db.execute(select(Cancion)).scalars().all()

    # Calcular puntuaciones para cada canción candidata
    canciones_recomendadas = [
        (cancion, calcular_puntuacion(cancion, caracteristicas)) 
        for cancion in canciones_disponibles
        if all(historial.cancion.id != cancion.id for historial in historial_canciones)  # Evitar repetir canciones ya escuchadas
    ]

    # Ordenar por puntuación de mayor a menor y tomar las 30 mejores
    canciones_recomendadas.sort(key=lambda x: x[1], reverse=True)

    canciones_dict = {
        cancion.id: {
            "fotoPortada": cancion.album.fotoPortada,
            "nombre": cancion.nombre
        }
        for cancion, _ in canciones_recomendadas[:30]
    }

    return canciones_dict
