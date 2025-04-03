from db.models import *
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from concurrent.futures import ThreadPoolExecutor

""" Analiza el historial para encontrar artistas, generos, albumes y playlists mas reproducidos. """
def extraer_caracteristicas(historial_canciones, historial_colecciones):
    artistas = {}
    generos = {}
    albumes = {}
    playlists = {}

    # Obtener info de las canciones
    for cancion in historial_canciones:
        artistas[cancion.Artista_correo] = artistas.get(cancion.Artista_correo, 0) + 1
        for genero in cancion.generosMusicales:
            generos[genero.nombre] = generos.get(genero.nombre, 0) + 1
        albumes[cancion.Album_id] = albumes.get(cancion.Album_id, 0) + 1

    # Obtener colecciones reproducidas (álbumes y playlists)
    for coleccion in historial_colecciones:
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
    stmt_historial_canciones = select(Cancion).join(HistorialCancion, HistorialCancion.Cancion_id == Cancion.id
                                             ).where(HistorialCancion.Oyente_correo == usuario.correo
                                             ).order_by(HistorialCancion.fecha.desc()                                              
                                             ).limit(50)

    stmt_historial_colecciones = select(Coleccion).join(HistorialColeccion, HistorialColeccion.Coleccion_id == Coleccion.id
                                             ).where(HistorialColeccion.Oyente_correo == usuario.correo
                                             ).order_by(HistorialColeccion.fecha.desc()                                              
                                             ).limit(50)

    historial_canciones = db.execute(stmt_historial_canciones).scalars().all()
    historial_colecciones = db.execute(stmt_historial_colecciones).scalars().all()

    # Extraer características de sus gustos
    caracteristicas = extraer_caracteristicas(historial_canciones, historial_colecciones)

    # Obtener todas las canciones disponibles en la plataforma
    query = (
        select(Cancion)
        .options(
            selectinload(Cancion.esParteDePlaylist),  # Carga las playlists en una sola consulta
            selectinload(Cancion.generosMusicales)     # Carga los géneros en una sola consulta
        )
    )
    canciones_disponibles = db.execute(query).scalars().all()

    # Filtrar canciones ya escuchadas
    canciones_candidatas = [
        cancion for cancion in canciones_disponibles
        if all(historial.id != cancion.id for historial in historial_canciones)
    ]

    canciones_recomendadas = [
        (cancion, calcular_puntuacion(cancion, caracteristicas)) for cancion in canciones_candidatas
    ]

    # Ordenar por puntuación de mayor a menor y tomar las 30 mejores
    canciones_recomendadas.sort(key=lambda x: x[1], reverse=True)

    canciones = [
        {
            "id": cancion.id,
            "nombreArtisticoArtista" : cancion.artista.nombreArtistico,
            "fotoPortada": cancion.album.fotoPortada,
            "nombre": cancion.nombre
        }
        for cancion, _ in canciones_recomendadas[:20]
    ]

    return canciones
