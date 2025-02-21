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

# Tabla intermedia para 'HistorialPlaylist'
class HistorialPlaylist(Base):
    __tablename__ = "HistorialPlaylist"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Playlist_nombre: Mapped[str] = mapped_column(ForeignKey("Playlist.nombre"), primary_key=True)
    Playlist_Usuario_Correo: Mapped[str] = mapped_column(ForeignKey("Playlist.Usuario_correo"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="historialPlaylist")
    playlist: Mapped["Playlist"] = relationship("Playlist")

# Tabla intermedia para 'HistorialCancion'
class HistorialCancion(Base):
    __tablename__ = "HistorialCancion"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Cancion_Usuario_Correo: Mapped[str] = mapped_column(ForeignKey("Cancion.Usuario_correo"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="historialCancion")
    cancion: Mapped["Cancion"] = relationship("Cancion")

# Tabla intermedia para "EstaEscuchando"
class EstaEscuchando(Base):
    __tablename__ = "EstaEscuchando"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Cancion_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Cancion.usuario_correo"), primary_key=True)
    minuto: Mapped[int] = mapped_column(nullable=False)
    segundo: Mapped[int] = mapped_column(nullable=False)

    # Restricción de minuto (0-60) a nivel de BD
    __table_args__ = (
        CheckConstraint('minuto BETWEEN 0 AND 100', name='check_volumen'),
    )

    # Restricción de minuto (0-60) a nivel de Python
    @validates("minuto")
    def validate_minuto(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Minuto debe estar entre 0 y 60")
        return value
    
    # Restricción de segundo (0-60) a nivel de BD
    __table_args__ = (
        CheckConstraint('segundo BETWEEN 0 AND 100', name='check_volumen'),
    )

    # Restricción de segundo (0-60) a nivel de Python
    @validates("segundo")
    def validate_segundo(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Segundo debe estar entre 0 y 60")
        return value

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="estaEscuchando")
    cancion: Mapped["Cancion"] = relationship("Cancion")

# Tabla intermedia para "Like"
like_table = Table(
    "Like", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo"), primary_key=True),
    Column("Noizzy_Usuario_correo", ForeignKey("Noizzy.Usuario_correo"), primary_key=True),
    Column("Noizzy_fechaHora", ForeignKey("Noizzy.fechaHora"), primary_key=True)
)

# Tabla intermedia para "EsParteDePlaylist"
class EsParteDePlaylist(Base):
    __tablename__ = "EsParteDePlaylist"

    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Cancion_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Cancion.usuario_correo"), primary_key=True)
    Album_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Album_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Cancion.usuario_correo"), primary_key=True)
    puesto: Mapped[int] = mapped_column(nullable=False)

# Tabla intermedia para "Pertenece"
pertenece_table = Table(
    "Pertenece", Base.metadata,
    Column("Cancion_nombre", ForeignKey("Cancion.nombre"), primary_key=True),
    Column("Cancion_Usuario_correo", ForeignKey("Cancion.Usuario_correo"), primary_key=True),
    Column("Genero_nombre", ForeignKey("Genero.nombre"), primary_key=True)
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
    
    # Relacion "Postea" con Noizzy (1 a N)
    noizzys: Mapped["Noizzy"] = relationship("Postea", back_populates="usuario", cascade="all, delete-orphan")

    # Relacion "Like" con Noizzy (N a M)
    liked: Mapped[list["Noizzy"]] = relationship(
        "Noizzy",
        secondary=like_table,
        back_populates="likes",
        cascade="all, delete-orphan"
    )

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

class Album(Base):
    __tablename__ = 'Album'

    nombre: Mapped[str] = mapped_column(String, primary_key=True)
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), primary_key=True)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(primary_key=True)

    # Relacion "CreaAlbum" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(back_populates="albumes")

    # Relacion "EsParteDeAlbum" con Artista (1 a N)
    canciones: Mapped[List["Cancion"]] = relationship(back_populates="album", cascade="all, delete-orphan")

class Playlist(Base):
    __tablename__ = 'Album'

    nombre: Mapped[str] = mapped_column(String, primary_key=True)
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), primary_key=True)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    privacidad: Mapped[bool] = mapped_column(primary_key=True)

    # Relacion "CreaPlaylist" con Artista (1 a N)
    usuario: Mapped["Artista"] = relationship(back_populates="playlists")

    # Relacion "EsParteDePlaylist" con Usuario (N a M)
    canciones: Mapped[List["Cancion"]] = relationship(
        "Cancion", 
        secondary="EsParteDePlaylist",  
        order_by="EsParteDePlaylist.puesto",
        back_populates="playlists"
    )

# Entidad Cancion
class Cancion(Base):
    __tablename__ = "Cancion"

    Artista_Usuario_correo: Mapped[str] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(primary_key=True)
    duracion: Mapped[int] = mapped_column(nullable=False)
    audio: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(nullable=False)
    reproducciones: Mapped[int] = mapped_column(nullable=False)
    
    # Relacion "EsParteDePlaylist" con Playlist (N a M)
    playlists: Mapped[List["Playlist"]] = relationship(
        "Playlist",
        secondary="EsParteDePlaylist",
        back_populates="canciones"
    )
    
    # Relacion "Referencia" con Noizzy (1 a N)
    noizzys: Mapped[List["Noizzy"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "Pertenece" con GeneroMusical (N a M)
    pertenece: Mapped[List["Pertenece"]] = relationship(
        "Pertenece",
        secondary="Pertenece",
        back_populates="canciones"
    )

# Entidad Genero Musical
class GeneroMusical(Base):
    __tablename__ = "GeneroMusical"
    
    nombre: Mapped[str] = mapped_column(primary_key=True)

    # Relacion "Pertenece" con Cancion (N a M)
    pertenece: Mapped[List["Pertenece"]] = relationship(
        "Pertenece",
        secondary="Pertenece",
        back_populates="generosMusicales"
    )
    

# Entidad Noizzy
class Noizzy(Base):
    __tablename__ = "Noizzy"
    
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(primary_key=True)
    texto: Mapped[str] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'noizzy',  
        'polymorphic_on': tipo  
    }

    # Relacion "Postea" con Usuario (1 a N)
    usuario: Mapped["Usuario"] = relationship(back_populates="noizzys")

    # Relacion "Responde" con Noizzito (1 a N)
    noizzitos: Mapped["Noizzito"] = relationship(back_populates="noizzy")

    # Relacion "Referencia" con Cancion (1 a N)
    cancion: Mapped["Noizzys"] = relationship(back_populates="noizzys")

    # Relacion "Like" con Usuario (N a M)
    likes: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary=like_table,
        back_populates="liked",
        cascade="all, delete-orphan"
    )

# Entidad Noizzito
class Noizzito(Noizzy):
    __tablename__ = 'Noizzito'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'noizzito',
    }

    # Relacion "Responde" con Noizzy (1 a N)
    noizzy: Mapped["Noizzy"] = relationship(back_populates="noizzitos")
