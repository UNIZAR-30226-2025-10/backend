from app.src.db.models import *
from app.src.db.db import get_db
from sqlalchemy.orm import Session

def insert_data(session: Session):
    # Recuperar al artista
    artista = session.get(Usuario, "usuario1@example.com")
    if not artista:
        print("Artista no encontrado.")
        return
    
    # Crear dos álbumes
    album1 = Album(nombre="Album1", Artista_Usuario_correo=artista.correo,
                   fotoPortada="album1.jpg", fechaPublicacion=date(2024, 1, 1))
    album2 = Album(nombre="Album2", Artista_Usuario_correo=artista.correo,
                   fotoPortada="album2.jpg", fechaPublicacion=date(2024, 2, 1))
    
    session.add_all([album1, album2])
    session.commit()

    # Crear cinco canciones
    canciones = [
        Cancion(nombre="Cancion 1", Artista_Usuario_correo=artista.correo, duracion=200, audio="cancion1.mp3", 
                fechaPublicacion=date(2024, 1, 1), reproducciones=0, Album_Artista_Usuario_correo=artista.correo, 
                Album_nombre=album1.nombre, puesto=1),
        Cancion(nombre="Cancion 2", Artista_Usuario_correo=artista.correo, duracion=180, audio="cancion2.mp3", 
                fechaPublicacion=date(2024, 1, 1), reproducciones=0, Album_Artista_Usuario_correo=artista.correo, 
                Album_nombre=album1.nombre, puesto=2),
        Cancion(nombre="Cancion 3", Artista_Usuario_correo=artista.correo, duracion=210, audio="cancion3.mp3", 
                fechaPublicacion=date(2024, 2, 1), reproducciones=0, Album_Artista_Usuario_correo=artista.correo, 
                Album_nombre=album2.nombre, puesto=1),
        Cancion(nombre="Cancion 4", Artista_Usuario_correo=artista.correo, duracion=190, audio="cancion4.mp3", 
                fechaPublicacion=date(2024, 2, 1), reproducciones=0, Album_Artista_Usuario_correo=artista.correo, 
                Album_nombre=album2.nombre, puesto=2),
        Cancion(nombre="Cancion 5", Artista_Usuario_correo=artista.correo, duracion=220, audio="cancion5.mp3", 
                fechaPublicacion=date(2024, 2, 1), reproducciones=0, Album_Artista_Usuario_correo=artista.correo, 
                Album_nombre=album2.nombre, puesto=3)
    ]

    session.add_all(canciones)
    session.commit()
    
    # Asociar canciones con géneros musicales
    generos = [GeneroMusical(nombre="Pop"), GeneroMusical(nombre="Rock"), 
               GeneroMusical(nombre="Indie")]
    
    session.add_all(generos)
    session.commit()

    canciones[0].generosMusicales.append(generos[0])
    canciones[1].generosMusicales.extend([generos[0], generos[1]])
    canciones[2].generosMusicales.extend([generos[0], generos[2]])
    canciones[3].generosMusicales.append(generos[2])
    canciones[4].generosMusicales.extend([generos[1], generos[2]])

    print(f"Canciones de {artista.nombreArtistico}:")
    for cancion in artista.canciones:
        generos = ", ".join([genero.nombre for genero in cancion.generosMusicales])  # Convierte la lista en una cadena
        print(f"- {cancion.nombre} ({cancion.album.nombre}) | {generos}")
    
    return
        
s = get_db()
insert_data(s)