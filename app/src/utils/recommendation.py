from db.models import *
from sqlalchemy import select
from concurrent.futures import ThreadPoolExecutor

""" Analiza el historial para encontrar artistas, generos, albumes y playlists mas reproducidos. """
def extraer_caracteristicas(historial_canciones, historial_colecciones):
    artistas = {}
    generos = {}
    albumes = {}
    playlists = {}

    # Obtener info de las canciones
    for historial in historial_canciones:
        cancion = historial.cancion
        if cancion:
            artistas[cancion.Artista_correo] = artistas.get(cancion.Artista_correo, 0) + 1
            for genero in cancion.generosMusicales:
                generos[genero.nombre] = generos.get(genero.nombre, 0) + 1
            albumes[cancion.Album_id] = albumes.get(cancion.Album_id, 0) + 1

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
    
    if cancion.Artista_correo in caracteristicas["artistas"]:
        puntuacion += caracteristicas["artistas"][cancion.Artista_correo] * 3  # Artista tiene más peso
    
    for genero in cancion.generosMusicales:
        if genero.nombre in caracteristicas["generos"]:
            puntuacion += caracteristicas["generos"][genero.nombre] * 2  # Género es importante
    
    if cancion.Album_id in caracteristicas["albumes"]:
        puntuacion += caracteristicas["albumes"][cancion.Album_id] * 1.5  # Álbum tiene peso medio
    
    for playlist in cancion.esParteDePlaylist:
        if playlist.Playlist_id in caracteristicas["playlists"]:
            puntuacion += caracteristicas["playlists"][playlist.Playlist_id]  # Playlists tienen peso bajo
    
    return puntuacion

""" Devuelve 30 canciones recomendadas para el usuario basado en su historial. """
def obtener_recomendaciones(usuario, db):
    # Obtener historial del usuario
    historial_canciones = usuario.historialCancion[:30]
    historial_colecciones = usuario.historialColeccion[:30]

    # Extraer características de sus gustos
    caracteristicas = extraer_caracteristicas(historial_canciones, historial_colecciones)

    # Obtener todas las canciones disponibles en la plataforma
    canciones_disponibles = db.execute(select(Cancion)).scalars().all()

    # Filtrar canciones ya escuchadas
    canciones_candidatas = [
        cancion for cancion in canciones_disponibles
        if all(historial.Cancion_id != cancion.id for historial in historial_canciones)
    ]

    # Calcular puntuaciones de forma concurrente
    def calcular(cancion):
        return cancion, calcular_puntuacion(cancion, caracteristicas)

    with ThreadPoolExecutor() as executor:
        canciones_recomendadas = list(executor.map(calcular, canciones_candidatas))

    # Ordenar por puntuación de mayor a menor y tomar las 30 mejores
    canciones_recomendadas.sort(key=lambda x: x[1], reverse=True)

    canciones = [
        {
            "id": cancion.id,
            "fotoPortada": cancion.album.fotoPortada,
            "nombre": cancion.nombre
        }
        for cancion, _ in canciones_recomendadas[:30]
    ]

    return canciones
