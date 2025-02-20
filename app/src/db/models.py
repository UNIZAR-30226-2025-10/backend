from datetime import datetime
from datetime import date
from datetime import time
from typing import List
from sqlalchemy import Table, Column, ForeignKey, Integer, CheckConstraint, String
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from db import get_db

class Base(DeclarativeBase):
    pass

# Tabla intermedia para 'Sigue'
sigue_table = Table(
    "Sigue", Base.metadata,
    Column("Seguidor_correo", ForeignKey("Usuario.correo"), primary_key=True),
    Column("Seguido_correo", ForeignKey("Usuario.correo"), primary_key=True)
)

# Tabla intermedia para 'Participante'
participante_table = Table(
    "Participante", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo"), primary_key=True),
    Column("Playlist_nombre", ForeignKey("Playlist.nombre"), primary_key=True),
    Column("Playlist_Usuario_correo", ForeignKey("Playlist.Usuario_correo"), primary_key=True)
)

# Tabla intermedia para 'Invitado'
invitado_table = Table(
    "Invitado", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo"), primary_key=True),
    Column("Playlist_nombre", ForeignKey("Playlist.nombre"), primary_key=True),
    Column("Playlist_Usuario_correo", ForeignKey("Playlist.Usuario_correo"), primary_key=True)
)

# Entidad ContraReset
class ContraReset(Base):
    __tablename__ = "ContraReset"
    
    token: Mapped[int] = mapped_column(primary_key=True)
    usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="contraReset", cascade="all, delete-orphan")

# Entidad Usuario
class Usuario(Base):
    __tablename__ = "Usuario"
    
    correo: Mapped[str] = mapped_column(primary_key=True)
    nombreUsuario: Mapped[str] = mapped_column(unique=True, nullable=False)
    contrasenya: Mapped[str] = mapped_column(nullable=False)
    fotoPerfil: Mapped[str] = mapped_column(nullable=False)
    volumen: Mapped[int] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',  
        'polymorphic_on': tipo  
    }

    # Restricción de volumen (0-100) a nivel de BD
    __table_args__ = (
        CheckConstraint('volumen BETWEEN 0 AND 100', name='check_volumen'),
    )

    # Restricción en volumen (0-100) a nivel de Python
    @validates("volumen")
    def validate_volumen(self, key, value):
        if not (0 <= value <= 100):
            raise ValueError("Volumen debe estar entre 0 y 100")
        return value

    # Relacion "Sigue" reflexiva (N a M) 
    seguidores: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary=sigue_table,
        primaryjoin=correo == sigue_table.c.Seguido_correo,
        secondaryjoin=correo == sigue_table.c.Seguidor_correo,
        backref="seguidos"
    )

    seguidos: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary=sigue_table,
        primaryjoin=correo == sigue_table.c.Seguido_correo,
        secondaryjoin=correo == sigue_table.c.Seguidor_correo,
        backref="seguidores"
    )

    # Relacion "Participante" con Playlist (N a M)
    participante: Mapped[list["Playlist"]] = relationship(
        "Playlist",
        secondary=participante_table,
        back_populates="participantes",
        cascade="all, delete-orphan"
    )

    # Relacion "Invitado" con Playlist (N a M)
    invitado: Mapped[list["Playlist"]] = relationship(
        "Playlist",
        secondary=invitado_table,
        back_populates="invitados",
        cascade="all, delete-orphan"
    )

    # Relacion "HistorialPlaylist" con Playlist (N a M)
    historialPlaylist: Mapped[list["HistorialPlaylist"]] = relationship(
        "HistorialPlaylist",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    # Relacion "HistorialCancion" con Cancion (N a M)
    historialCancion: Mapped[list["HistorialCancion"]] = relationship(
        "HistorialCancion",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    # Relacion "Cambia" con ContraReset (1 a 1)
    contraReset: Mapped["ContraReset"] = relationship(  # Puede ser None
        "ContraReset", uselist=False, back_populates="usuario", cascade="all, delete-orphan"
    )

    # Relacion "EstaEscuchando" con Usuario (1 a N)
    estaEscuchando: Mapped["EstaEscuchando"] = relationship(
        "EstaEscuchando",
        uselist=False,  # Un usuario solo puede estar escuchando una canción a la vez
        back_populates="usuario",
        cascade="all, delete-orphan"
    )
    
    # Relacion "Postea" con Usuario (1 a N)
    noizzys: Mapped["Noizzy"] = relationship(back_populates="usuario")

class Pendiente(Usuario):
    __tablename__ = 'Pendiente'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    codigo: Mapped[int] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'pendiente',
    }

class Artista(Usuario):
    __tablename__ = 'Artista'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)
    biografia: Mapped[str] = mapped_column(nullable=False)

    # Relacion "CreaAlbum" con Album (1 a N)
    albumes: Mapped[List["Album"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "CreaCancion" con Cancion (1 a N)
    canciones: Mapped[List["Cancion"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'artista',
    }