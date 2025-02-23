from datetime import datetime
from datetime import date
from datetime import time
from triggers import trg_estaInvitado, trg_eliminarInvitado, trg_noParticipante, trg_10Playlists, trg_50Canciones
from sqlalchemy import Table, Column, ForeignKey, Integer, CheckConstraint, String, event
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase, validates

class Base(DeclarativeBase):
    pass

# Tabla intermedia para 'Sigue'
sigue_table = Table(
    "Sigue", Base.metadata,
    Column("Seguidor_correo", ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True),
    Column("Seguido_correo", ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("Seguidor_correo != Seguido_correo", name="chk_noAutoSeguimiento")
)

# Tabla intermedia para 'Participante'
participante_table = Table(
    "Participante", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_nombre", ForeignKey("Playlist.nombre", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_Usuario_correo", ForeignKey("Playlist.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("Usuario_correo != Playlist_Usuario_correo", name="chk_participanteNoCreador")
)
event.listen(participante_table, "after_create", trg_estaInvitado)
event.listen(participante_table, "after_create", trg_eliminarInvitado)

# Tabla intermedia para 'Invitado'
invitado_table = Table(
    "Invitado", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_nombre", ForeignKey("Playlist.nombre", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_Usuario_correo", ForeignKey("Playlist.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("Usuario_correo != Playlist_Usuario_correo", name="chk_invitadoNoCreador")
)
event.listen(invitado_table, "after_create", trg_noParticipante)

# Tabla intermedia para 'HistorialPlaylist'
class HistorialPlaylist(Base):
    __tablename__ = "HistorialPlaylist"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Playlist_nombre: Mapped[str] = mapped_column(ForeignKey("Playlist.nombre"), primary_key=True)
    Playlist_Usuario_Correo: Mapped[str] = mapped_column(ForeignKey("Playlist.Usuario_correo"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    # Relaciones con Usuario y Playlist
    usuario: Mapped["Usuario"] = relationship(back_populates="historialPlaylist")
    playlist: Mapped["Playlist"] = relationship(back_populates="historialPlaylist")
event.listen(HistorialPlaylist, "after_insert", trg_10Playlists)

# Tabla intermedia para 'HistorialCancion'
class HistorialCancion(Base):
    __tablename__ = "HistorialCancion"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Cancion_Artista_Usuario_Correo: Mapped[str] = mapped_column(ForeignKey("Cancion.Artista_Usuario_correo"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="historialCancion")
    cancion: Mapped["Cancion"] = relationship(back_populates="historialCancion")
event.listen(HistorialCancion, "after_insert", trg_50Canciones)

# Tabla intermedia para "EstaEscuchando"
class EstaEscuchando(Base):
    __tablename__ = "EstaEscuchando"

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), nullable=False)
    Cancion_Artista_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Cancion.Artista_Usuario_correo"), nullable=False)
    minuto: Mapped[int] = mapped_column(nullable=False)
    segundo: Mapped[int] = mapped_column(nullable=False)

    # Restricción de minuto (0-60) a nivel de BD
    __table_args__ = (
        CheckConstraint('minuto BETWEEN 0 AND 60', name='chk_minuto'),
    )

    # Restricción de minuto (0-60) a nivel de Python
    @validates("minuto")
    def validate_minuto(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Minuto debe estar entre 0 y 60")
        return value
    
    # Restricción de segundo (0-60) a nivel de BD
    __table_args__ = (
        CheckConstraint('segundo BETWEEN 0 AND 60', name='chk_segundo'),
    )

    # Restricción de segundo (0-60) a nivel de Python
    @validates("segundo")
    def validate_segundo(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Segundo debe estar entre 0 y 60")
        return value

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="estaEscuchando")
    cancion: Mapped["Cancion"] = relationship("Cancion", back_populates="estaEscuchando")

# Tabla intermedia para "Like"
like_table = Table(
    "Like", Base.metadata,
    Column("Usuario_correo", ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True),
    Column("Noizzy_id", ForeignKey("Noizzy.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para "EsParteDePlaylist"
class EsParteDePlaylist(Base):
    __tablename__ = "EsParteDePlaylist"

    Cancion_nombre: Mapped[str] = mapped_column(ForeignKey("Cancion.nombre"), primary_key=True)
    Cancion_Artista_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Cancion.Artista_Usuario_correo"), primary_key=True)
    Playlist_nombre: Mapped[str] = mapped_column(ForeignKey("Playlist.nombre"), primary_key=True)
    Playlist_Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Playlist.Usuario_correo"), primary_key=True)
    puesto: Mapped[int] = mapped_column(nullable=False)

    cancion: Mapped["Cancion"] = relationship(back_populates="esParteDePlaylist")
    playlist: Mapped["Playlist"] = relationship(back_populates="esParteDePlaylist")

# Tabla intermedia para "Pertenece"
pertenece_table = Table(
    "Pertenece", Base.metadata,
    Column("Cancion_nombre", ForeignKey("Cancion.nombre", ondelete="CASCADE"), primary_key=True),
    Column("Cancion_Artista_Usuario_correo", ForeignKey("Cancion.Artista_Usuario_correo", ondelete="CASCADE"), primary_key=True),
    Column("GeneroMusical_nombre", ForeignKey("GeneroMusical.nombre", ondelete="CASCADE"), primary_key=True)
)

# Entidad ContraReset
class ContraReset(Base):
    __tablename__ = "ContraReset"
    
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo"), primary_key=True)
    token: Mapped[int] = mapped_column(nullable=False)

    # Relacion "Cambio" 1 a 1 con Usuario    
    usuario: Mapped["Usuario"] = relationship(uselist=False, back_populates="contraReset")

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
        CheckConstraint('volumen BETWEEN 0 AND 100', name='chk_volumen'),
    )

    # Restricción en volumen (0-100) a nivel de Python
    @validates("volumen")
    def validate_volumen(self, key, value):
        if not (0 <= value <= 100):
            raise ValueError("Volumen debe estar entre 0 y 100")
        return value
    
    # Relacion "CreaPlaylist" con Playlist (1 a N)
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")

    # Relacion "Seguidos" y "Seguidores"
    seguidos: Mapped[list["Usuario"]] = relationship(secondary=sigue_table,
        primaryjoin=correo == sigue_table.c.Seguido_correo, secondaryjoin=correo == sigue_table.c.Seguidor_correo,
        backref="seguidores", passive_deletes=True)

    # Relacion "Participante" con Playlist (N a M)
    participante: Mapped[list["Playlist"]] = relationship(secondary=participante_table, back_populates="participantes",
        passive_deletes=True)
    
    # Relacion "Invitado" con Playlist (N a M)
    invitado: Mapped[list["Playlist"]] = relationship(secondary=invitado_table, back_populates="invitados",
       passive_deletes=True)
    
    # Relacion "HistorialCancion" con Cancion (N a M)
    cancionesHistorial: Mapped[list["Cancion"]] = relationship(secondary="HistorialCancion", back_populates="usuariosHistorial",
        cascade="all, delete-orphan")

    # Relacion con HistorialPlaylist (1:N)
    historialPlaylist: Mapped[list["HistorialPlaylist"]] = relationship(back_populates="usuario",
        cascade="all, delete-orphan")

    # Relacion con Playlist (N:M) a traves de HistorialPlaylist, ordenada por fechaHora DESC
    playlistsHistorial: Mapped[list["Playlist"]] = relationship(secondary="HistorialPlaylist", back_populates="usuariosHistorial",
        cascade="all, delete-orphan", order_by="HistorialPlaylist.fechaHora.desc()")  # Ordenar por fechaHora de HistorialPlaylist
    
    # Relacion con tabla intermedia "HistorialCancion"
    historialCancion: Mapped[list["HistorialCancion"]] = relationship(back_populates="usuario",
        cascade="all, delete-orphan")

    # Relacion "HistorialCancion" con Cancion (N a M)
    cancionesHistorial: Mapped[list["Cancion"]] = relationship(secondary="HistorialCancion", back_populates="usuariosHistorial",
        cascade="all, delete-orphan", order_by="HistorialCancion.fechaHora.desc()")  # Ordenar por fechaHora de HistorialCancion

    # Relacion "Cambio" con ContraReset (1 a 1)
    contraReset: Mapped["ContraReset"] = relationship(uselist=False, back_populates="usuario",
        cascade="all, delete-orphan")
    
    # Relacion con tabla intermedia "EstaEscuchando"
    estaEscuchando: Mapped["EstaEscuchando"] = relationship(uselist=False, back_populates="usuario",
        cascade="all, delete-orphan")

    # Relacion "EstaEscuchando" con Usuario (1 a N)
    cancionActual: Mapped["Cancion"] = relationship(uselist=False, secondary="EstaEscuchando")
    
    # Relacion "Postea" con Noizzy (1 a N)
    noizzys: Mapped[list["Noizzy"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    
    # Relacion "Like" con Noizzy (N a M)
    liked: Mapped[list["Noizzy"]] = relationship(secondary=like_table, back_populates="likes",
        passive_deletes=True)
        
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
    albumes: Mapped[list["Album"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "CreaCancion" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'artista',
    }

class Album(Base):
    __tablename__ = 'Album'

    nombre: Mapped[str] = mapped_column(String, primary_key=True)
    Artista_Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), primary_key=True)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(nullable=False)

    # Relacion "CreaAlbum" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(uselist=False, back_populates="albumes")

    # Relacion "EsParteDeAlbum" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="album", cascade="all, delete-orphan",
        order_by="Cancion.puesto")

class Playlist(Base):
    __tablename__ = 'Playlist'

    nombre: Mapped[str] = mapped_column(String, primary_key=True)
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    privacidad: Mapped[bool] = mapped_column(nullable=False)

    # Relacion con tabla intermedia "EsParteDePlaylist"
    esParteDePlaylist: Mapped[list["EsParteDePlaylist"]] = relationship(back_populates="playlist",
        cascade="all, delete-orphan")
    
    # Relacion "EsParteDePlaylist" con Playlist (N a M)
    canciones: Mapped[list["Cancion"]] = relationship(secondary="EsParteDePlaylist", back_populates="playlists",
        order_by="EsParteDePlaylist.puesto")

    # Relacion directa con la tabla intermedia "HistorialPlaylist" (1:N)
    historialPlaylist: Mapped[list["HistorialPlaylist"]] = relationship(back_populates="playlist",
        cascade="all, delete-orphan")

    # Relacion indirecta con Usuario (N:M) a traves de HistorialPlaylist
    usuariosHistorial: Mapped[list["Usuario"]] = relationship(secondary="HistorialPlaylist", back_populates="playlistsHistorial",
        cascade="all, delete-orphan")

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Participantes"
    participantes: Mapped[list["Usuario"]] = relationship(secondary=participante_table, back_populates="participante",
        passive_deletes=True)

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Invitado"
    invitados: Mapped[list["Usuario"]] = relationship(secondary=invitado_table, back_populates="invitado",
        passive_deletes=True)

    # Relacion "CreaPlaylist" con Usuario (1 a N)
    usuario: Mapped["Usuario"] = relationship(uselist=False, back_populates="playlists")
    
    # Relacion "EsParteDePlaylist" con Usuario (N a M)
    canciones: Mapped[list["Cancion"]] = relationship(
        "Cancion", 
        secondary="EsParteDePlaylist",  
        order_by="EsParteDePlaylist.puesto",
        back_populates="playlists"
    )
    
# Entidad Cancion
class Cancion(Base):
    __tablename__ = "Cancion"

    Artista_Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), primary_key=True)
    nombre: Mapped[str] = mapped_column(primary_key=True)
    duracion: Mapped[int] = mapped_column(nullable=False)
    audio: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(nullable=False)
    reproducciones: Mapped[int] = mapped_column(nullable=False)
    Album_Artista_Usuario_correo:  Mapped[str] = mapped_column(ForeignKey('Album.Artista_Usuario_correo'), nullable=False)
    Album_nombre: Mapped[str] = mapped_column(ForeignKey('Album.nombre'), nullable=False)
    puesto: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("Artista_Usuario_correo == Album_Artista_Usuario_correo", name="chk_cancionAlbum"),
    )

    # Relacion "CreaCancion" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(uselist=False, back_populates="canciones")

    # Relacion con tabla intermedia "HistorialCancion"
    historialCancion: Mapped[list["HistorialCancion"]] = relationship(back_populates="cancion",
        cascade="all, delete-orphan")

    # Relacion con "Usuario" (N:M) a traves de la tabla intermedia "HistorialCancion"
    usuariosHistorial: Mapped[list["Usuario"]] = relationship(secondary="HistorialCancion", back_populates="cancionesHistorial",
        cascade="all, delete-orphan")
    
    # Relacion con tabla intermedia "EsParteDePlaylist"
    esParteDePlaylist: Mapped[list["EsParteDePlaylist"]] = relationship(back_populates="cancion",
        cascade="all, delete-orphan")
    
    # Relacion "EsParteDePlaylist" con Playlist (N a M)
    playlists: Mapped[list["Playlist"]] = relationship(secondary="EsParteDePlaylist", back_populates="canciones")
    
    # Relacion "Referencia" con Noizzy (1 a N)
    noizzys: Mapped[list["Noizzy"]] = relationship(back_populates="cancion", cascade="all, delete-orphan")
    
    # Relacion "Pertenece" con GeneroMusical (N a M)
    generosMusicales: Mapped[list["GeneroMusical"]] = relationship(secondary=pertenece_table,
        back_populates="canciones", passive_deletes=True)

    # Relacion "EsParteDeAlbum" con Album (1 a N)
    album: Mapped["Album"] = relationship(uselist=False, back_populates="canciones")
    
    # Relacion "EstaEscuchando" con Usuario (1 a N)
    estaEscuchando: Mapped["EstaEscuchando"] = relationship(uselist=False, back_populates="cancion",
        cascade="all, delete-orphan")

# Entidad Genero Musical
class GeneroMusical(Base):
    __tablename__ = "GeneroMusical"
    
    nombre: Mapped[str] = mapped_column(primary_key=True)
    
    # Relacion "Pertenece" con Cancion (N a M)
    canciones: Mapped[list["Cancion"]] = relationship(secondary=pertenece_table, back_populates="generosMusicales",
        passive_deletes=True)

# Entidad Noizzy
class Noizzy(Base):
    __tablename__ = "Noizzy"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # Id necesario por conflictos herencia y clave foranea compuesta
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), nullable=False)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)
    texto: Mapped[str] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'noizzy',  
        'polymorphic_on': tipo  
    }

    # Relacion "Postea" con Usuario (1 a N)
    usuario: Mapped["Usuario"] = relationship(uselist=False, back_populates="noizzys")

    # Relacion "Responde" con Noizzito (1 a N)
    noizzitos: Mapped[list["Noizzito"]] = relationship(back_populates="noizzy", cascade="all, delete-orphan")

    # Relacion "Referencia" con Cancion (1 a N)
    cancion: Mapped["Cancion"] = relationship(uselist=False, back_populates="noizzys")
    
    # Relacion "Like" con Usuario (N a M)
    likes: Mapped[list["Usuario"]] = relationship(secondary=like_table, back_populates="liked",
        passive_deletes=True)
    
# Entidad Noizzito
class Noizzito(Noizzy):
    __tablename__ = 'Noizzito'

    id: Mapped[int] = mapped_column(ForeignKey('Noizzy.id'), primary_key=True)
    Noizzy_id: Mapped[int] = mapped_column(ForeignKey('Noizzy.id'))

    __mapper_args__ = {
        'polymorphic_identity': 'noizzito',
        'inherit_condition': (id == Noizzy.id)
    }

    __table_args__ = (
        CheckConstraint("id != Noizzy_id", name="check_no_self_response"),
    )

    # Relacion "Responde" con Noizzy (1 a N)
    noizzy: Mapped["Noizzy"] = relationship(uselist=False, back_populates="noizzitos")
