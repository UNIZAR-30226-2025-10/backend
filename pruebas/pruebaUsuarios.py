from app.src.db.models import *
from app.src.db.db import get_db

session = get_db()

usuario1 = Artista(
    correo="usuario1@example.com",
    nombreUsuario="Usuario1",
    contrasenya="segura123",
    fotoPerfil="perfil.jpg",
    volumen=50,
    tipo="artista",
    nombreArtistico="User",
    biografia="loquesea"
)
session.add(usuario1)

usuario2 = Usuario(
    correo="usuario2@example.com",
    nombreUsuario="Usuario2",
    contrasenya="clave123",
    fotoPerfil="otra.jpg",
    volumen=80,
    tipo="usuario"
)
session.add(usuario2)

usuario1.seguidos.append(usuario2)
session.commit()

for u in usuario2.seguidores:
    print(f"{u.nombreUsuario}")