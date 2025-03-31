from datetime import datetime
from sqlalchemy import Table, Column, ForeignKey, CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.types import JSON

class Base(DeclarativeBase):
    pass

# Tabla intermedia para 'Sigue'
sigue_table = Table(
    "Sigue", Base.metadata,
    Column("Seguidor_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Seguido_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("Seguidor_correo != Seguido_correo", name="chk_noAutoSeguimiento")
)

# Tabla intermedia para 'Participante'
participante_table = Table(
    "Participante", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_id", String, ForeignKey("Playlist.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'Invitado'
invitado_table = Table(
    "Invitado", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_id", String, ForeignKey("Playlist.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'Featuring'
featuring_table = Table(
    "Featuring", Base.metadata,
    Column("Artista_correo", String, ForeignKey("Artista.correo", ondelete="CASCADE"), primary_key=True),
    Column("Cancion_id", String, ForeignKey("Cancion.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'NotificacionCancion'
notificacionCancion_table = Table(
    "NotificacionCancion", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Cancion_id", String, ForeignKey("Cancion.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'NotificacionAlbum'
notificacionAlbum_table = Table(
    "NotificacionAlbum", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Album_id", String, ForeignKey("Album.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'Lee'
sin_leer_table = Table(
    "SinLeer", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Noizzy_id", String, ForeignKey("Noizzy.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para 'HistorialColeccion'
class HistorialColeccion(Base):
    __tablename__ = "HistorialColeccion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True)
    Coleccion_id: Mapped[str] = mapped_column(ForeignKey("Coleccion.id", ondelete="CASCADE"), primary_key=True)
    fecha: Mapped[datetime] = mapped_column(nullable=False)

    # Relaciones con Usuario y Playlist
    oyente: Mapped["Oyente"] = relationship(back_populates="historialColeccion")
    coleccion: Mapped["Coleccion"] = relationship(back_populates="historialColeccion")

# Tabla intermedia para 'HistorialCancion'
class HistorialCancion(Base):
    __tablename__ = "HistorialCancion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True)
    Cancion_id: Mapped[str] = mapped_column(ForeignKey("Cancion.id", ondelete="CASCADE"), primary_key=True)
    fecha: Mapped[datetime] = mapped_column(nullable=False)

    oyente: Mapped["Oyente"] = relationship(back_populates="historialCancion")
    cancion: Mapped["Cancion"] = relationship(back_populates="historialCancion")

# Tabla intermedia para "EstaEscuchandoCancion"
class EstaEscuchandoCancion(Base):
    __tablename__ = "EstaEscuchandoCancion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True)
    Cancion_id: Mapped[int] = mapped_column(ForeignKey("Cancion.id", ondelete="CASCADE"), nullable=False)
    progreso: Mapped[int] = mapped_column(nullable=False)

    # Restricciones a nivel de BD
    __table_args__ = (
        CheckConstraint('progreso >= 0', name='chk_progreso'),
    )

    oyente: Mapped["Oyente"] = relationship(back_populates="estaEscuchandoCancion")
    cancion: Mapped["Cancion"] = relationship(back_populates="estaEscuchandoCancion")

# Tabla intermedia para "EstaEscuchandoColeccion"
class EstaEscuchandoColeccion(Base):
    __tablename__ = "EstaEscuchandoColeccion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True)
    Coleccion_id: Mapped[int] = mapped_column(ForeignKey("Coleccion.id", ondelete="CASCADE"), nullable=False)
    modo: Mapped[str] = mapped_column(nullable=False)
    index: Mapped[int] = mapped_column(nullable=False)
    orden: Mapped[list[int]] = mapped_column(JSON, nullable=False)  # Almacenamos como JSON

    # Restricciones a nivel de BD
    __table_args__ = (
        CheckConstraint("modo IN ('aleatorio', 'enBucle', 'enOrden')", name='chk_modo'),
    )

    oyente: Mapped["Oyente"] = relationship(back_populates="estaEscuchandoColeccion")
    coleccion: Mapped["Coleccion"] = relationship(back_populates="estaEscuchandoColeccion")
    

# Tabla intermedia para "Like"
like_table = Table(
    "Like", Base.metadata,
    Column("Oyente_correo", ForeignKey("Oyente.correo", ondelete="CASCADE"), primary_key=True),
    Column("Noizzy_id", ForeignKey("Noizzy.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para "EsParteDePlaylist"
class EsParteDePlaylist(Base):
    __tablename__ = "EsParteDePlaylist"

    Cancion_id: Mapped[str] = mapped_column(ForeignKey("Cancion.id", ondelete="CASCADE"), primary_key=True)
    Playlist_id: Mapped[str] = mapped_column(ForeignKey("Playlist.id", ondelete="CASCADE"), primary_key=True)
    fecha: Mapped[datetime] = mapped_column(nullable=False)

    cancion: Mapped["Cancion"] = relationship(back_populates="esParteDePlaylist")
    playlist: Mapped["Playlist"] = relationship(back_populates="esParteDePlaylist")

# Tabla intermedia para "Pertenece"
pertenece_table = Table(
    "Pertenece", Base.metadata,
    Column("Cancion_id", ForeignKey("Cancion.id", ondelete="CASCADE"), primary_key=True),
    Column("GeneroMusical_nombre", ForeignKey("GeneroMusical.nombre", ondelete="CASCADE"), primary_key=True),
)

# Entidad ContraReset
class ContraReset(Base):
    __tablename__ = "ContraReset"
    
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey("Usuario.correo", ondelete="CASCADE"), primary_key=True)
    codigo: Mapped[str] = mapped_column(nullable=False)

# Entidad Usuario
class Usuario(Base):
    __tablename__ = "Usuario"
    
    correo: Mapped[str] = mapped_column(primary_key=True)
    nombreUsuario: Mapped[str] = mapped_column(unique=True, nullable=False)
    contrasenya: Mapped[str] = mapped_column(nullable=False)
    tokenVersion: Mapped[int] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)
    sesionActiva: Mapped[bool] = mapped_column(nullable=False)
    

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',  
        'polymorphic_on': tipo  
    }

    # Constraint para tipo
    __table_args__ = (
        CheckConstraint("tipo IN ('admin', 'pendiente', 'valido', 'oyente', 'artista')", 
                        name="chk_tipoUsuario"),)

# Entidad Admin
class Admin(Usuario):
    __tablename__ = 'Admin'

    correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }

# Entidad Pendiente
class Pendiente(Usuario):
    __tablename__ = 'Pendiente'

    correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'pendiente',
    }

# Entidad Valido
class Valido(Usuario):
    __tablename__ = 'Valido'

    correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)
    codigo: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'valido',
    }

# Entidad Oyente
class Oyente(Usuario):
    __tablename__ = "Oyente"
    
    correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)
    fotoPerfil: Mapped[str] = mapped_column(nullable=False)
    volumen: Mapped[int] = mapped_column(nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'oyente'
    }
    
    # Restricción de volumen (0-100) a nivel de BD
    __table_args__ = (
        CheckConstraint('volumen BETWEEN 0 AND 100', name='chk_volumen'),
    )

    # Relacion "CreaPlaylist" con Playlist (1 a N)
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="oyente", cascade="all, delete-orphan")

    # Relacion "Seguidos" y "Seguidores"
    seguidos: Mapped[list["Oyente"]] = relationship(
        secondary=sigue_table,
        primaryjoin=correo == sigue_table.c.Seguidor_correo,  # El usuario actual es el seguidor
        secondaryjoin=correo == sigue_table.c.Seguido_correo,  # Se une con los usuarios seguidos
        backref="seguidores", passive_deletes=True
    )

    # Relacion "Participante" con Playlist (N a M)
    participante: Mapped[list["Playlist"]] = relationship(secondary=participante_table, back_populates="participantes",
        passive_deletes=True)
    
    # Relacion "Invitado" con Playlist (N a M)
    invitado: Mapped[list["Playlist"]] = relationship(secondary=invitado_table, back_populates="invitados",
       passive_deletes=True)
    
    # Relacion con HistorialColeccion (N:M)
    historialColeccion: Mapped[list["HistorialColeccion"]] = relationship(back_populates="oyente",
        cascade="all, delete")

    # Relacion con tabla intermedia "HistorialCancion"
    historialCancion: Mapped[list["HistorialCancion"]] = relationship(back_populates="oyente",
        cascade="all, delete")
    
    # Relacion con tabla intermedia "EstaEscuchandoCancion"
    estaEscuchandoCancion: Mapped["EstaEscuchandoCancion"] = relationship(uselist=False, back_populates="oyente",
        cascade="all, delete-orphan")
    
    # Relacion con tabla intermedia "EstaEscuchandoColeccion"
    estaEscuchandoColeccion: Mapped["EstaEscuchandoColeccion"] = relationship(uselist=False, back_populates="oyente",
        cascade="all, delete-orphan")
        
    # Relacion "Postea" con Noizzy (1 a N)
    noizzys: Mapped[list["Noizzy"]] = relationship(back_populates="oyente", cascade="all, delete-orphan")
    
    # Relacion "Like" con Noizzy (N a M)
    liked: Mapped[list["Noizzy"]] = relationship(secondary=like_table, back_populates="likes",
        passive_deletes=True)
    
    # Relacion "NotificacionCancion" con Cancion (N a M)
    notificacionesCancion: Mapped[list["Cancion"]] = relationship(secondary=notificacionCancion_table,
        back_populates="notificados", passive_deletes=True)

    # Relacion "NotificacionAlbum" con Album (N a M)
    notificacionesAlbum: Mapped[list["Album"]] = relationship(secondary=notificacionAlbum_table,
        back_populates="notificados", passive_deletes=True)
    
    # Relacion "Lee" con Noizzy (N a M)
    leidos: Mapped[list["Noizzy"]] = relationship(secondary=sin_leer_table, back_populates="lectores", 
        passive_deletes=True)
 

class Artista(Oyente):
    __tablename__ = 'Artista'

    correo: Mapped[str] = mapped_column(ForeignKey('Oyente.correo', ondelete="CASCADE"), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)
    biografia: Mapped[str] = mapped_column(nullable=True)

    # Relacion "CreaAlbum" con Album (1 a N)
    albumes: Mapped[list["Album"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "CreaCancion" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "Featuring" con Cancion (N a M)
    featured: Mapped[list["Cancion"]] = relationship(secondary=featuring_table, back_populates="featuring",
        passive_deletes=True)

    __mapper_args__ = {
        'polymorphic_identity': 'artista',
    }

class Coleccion(Base):
    __tablename__ = 'Coleccion'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(nullable=False)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)
    fecha: Mapped[datetime] = mapped_column(nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'coleccion',  
        'polymorphic_on': tipo  
    }

    # Constraint para tipo
    __table_args__ = (
        CheckConstraint("tipo IN ('album', 'playlist')", 
                        name="chk_tipoColeccion"),)

    # Relacion directa con la tabla intermedia "HistorialColeccion" (N a M)
    historialColeccion: Mapped[list["HistorialColeccion"]] = relationship(back_populates="coleccion",
        cascade="all, delete")
    
    # Relacion "EstaEscuchandoColeccion" con Oyente (1 a N)
    estaEscuchandoColeccion: Mapped["EstaEscuchandoColeccion"] = relationship(uselist=False, back_populates="coleccion",
        cascade="all, delete-orphan")

class Album(Coleccion):
    __tablename__ = 'Album'

    id: Mapped[int] = mapped_column(ForeignKey('Coleccion.id', ondelete="CASCADE"), primary_key=True)
    Artista_correo: Mapped[str] = mapped_column(ForeignKey('Artista.correo', ondelete="CASCADE"), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'album',
    }

    # Relacion "CreaAlbum" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(uselist=False, back_populates="albumes")

    # Relacion "EsParteDeAlbum" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="album", cascade="all, delete-orphan",
        order_by="Cancion.puesto")
    
    # Relacion "NotificacionAlbum" con Oyente (N a M)
    notificados: Mapped[list["Oyente"]] = relationship(secondary=notificacionAlbum_table, 
        back_populates="notificacionesAlbum", passive_deletes=True)

class Playlist(Coleccion):
    __tablename__ = 'Playlist'

    id: Mapped[int] = mapped_column(ForeignKey('Coleccion.id', ondelete="CASCADE"), primary_key=True)
    Oyente_correo: Mapped[str] = mapped_column(ForeignKey('Oyente.correo', ondelete="CASCADE"), nullable=False)
    privacidad: Mapped[bool] = mapped_column(nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'playlist',
    }

    # Relacion con tabla intermedia "EsParteDePlaylist"
    esParteDePlaylist: Mapped[list["EsParteDePlaylist"]] = relationship(back_populates="playlist",
        cascade="all, delete-orphan")

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Participantes"
    participantes: Mapped[list["Oyente"]] = relationship(secondary=participante_table, back_populates="participante",
        passive_deletes=True)

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Invitado"
    invitados: Mapped[list["Oyente"]] = relationship(secondary=invitado_table, back_populates="invitado",
        passive_deletes=True)

    # Relacion "CreaPlaylist" con Oyente (1 a N)
    oyente: Mapped["Oyente"] = relationship(uselist=False, back_populates="playlists")
    
# Entidad Cancion
class Cancion(Base):
    __tablename__ = "Cancion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Artista_correo: Mapped[str] = mapped_column(ForeignKey('Artista.correo', ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(nullable=False)
    duracion: Mapped[int] = mapped_column(nullable=False)   # Duracion en segundos
    audio: Mapped[str] = mapped_column(nullable=False)
    fecha: Mapped[datetime] = mapped_column(nullable=False)
    reproducciones: Mapped[int] = mapped_column(nullable=False)
    Album_id:  Mapped[int] = mapped_column(ForeignKey('Album.id', ondelete="CASCADE"), nullable=False)
    puesto: Mapped[int] = mapped_column(nullable=False)

    # Puestos unicos en un album
    __table_args__ = (
        UniqueConstraint("Album_id", "puesto", name="uq_puestoAlbum"),
    )

    # Relacion "CreaCancion" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(uselist=False, back_populates="canciones")

    # Relacion con tabla intermedia "HistorialCancion"
    historialCancion: Mapped[list["HistorialCancion"]] = relationship(back_populates="cancion",
        cascade="all, delete")

    # Relacion con tabla intermedia "EsParteDePlaylist"
    esParteDePlaylist: Mapped[list["EsParteDePlaylist"]] = relationship(back_populates="cancion",
        cascade="all, delete")
    
    # Relacion "Referencia" con Noizzy (1 a N)
    noizzys: Mapped[list["Noizzy"]] = relationship(back_populates="cancion", cascade="all, delete-orphan")
    
    # Relacion "Pertenece" con GeneroMusical (N a M)
    generosMusicales: Mapped[list["GeneroMusical"]] = relationship(secondary=pertenece_table,
        back_populates="canciones", passive_deletes=True)

    # Relacion "EsParteDeAlbum" con Album (1 a N)
    album: Mapped["Album"] = relationship(uselist=False, back_populates="canciones")
    
    # Relacion "EstaEscuchandoCancion" con Oyente (1 a N)
    estaEscuchandoCancion: Mapped["EstaEscuchandoCancion"] = relationship(uselist=False, back_populates="cancion",
        cascade="all, delete-orphan")
    
    # Relacion "Featuring" con Artista (N a M)
    featuring: Mapped[list["Artista"]] = relationship(secondary=featuring_table, 
        back_populates="featured", passive_deletes=True)
    
    # Relacion "NotificacionCancion" con Oyente (N a M)
    notificados: Mapped[list["Oyente"]] = relationship(secondary=notificacionCancion_table, 
        back_populates="notificacionesCancion", passive_deletes=True)

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
    Oyente_correo: Mapped[str] = mapped_column(ForeignKey('Oyente.correo', ondelete="CASCADE"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(nullable=False)
    texto: Mapped[str] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)
    Cancion_id: Mapped[str] = mapped_column(ForeignKey('Cancion.id'), nullable=True)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'noizzy',  
        'polymorphic_on': tipo  
    }

    # Relacion "Postea" con Oyente (1 a N)
    oyente: Mapped["Oyente"] = relationship(uselist=False, back_populates="noizzys")

    # Relacion "Responde" con Noizzito (1 a N)
    noizzitos: Mapped[list["Noizzito"]] = relationship(back_populates="noizzy", foreign_keys="[Noizzito.Noizzy_id]", 
        cascade="all, delete-orphan")

    # Relacion "Referencia" con Cancion (1 a N)
    cancion: Mapped["Cancion"] = relationship(uselist=False, back_populates="noizzys")
    
    # Relacion "Like" con Oyente (N a M)
    likes: Mapped[list["Oyente"]] = relationship(secondary=like_table, back_populates="liked",
        passive_deletes=True)
    
    # Relacion "Lee" con Oyente (N a M)
    lectores: Mapped[list["Oyente"]] = relationship(secondary=sin_leer_table, back_populates="leidos", 
        passive_deletes=True)
    
# Entidad Noizzito
class Noizzito(Noizzy):
    __tablename__ = 'Noizzito'

    id: Mapped[int] = mapped_column(ForeignKey('Noizzy.id', ondelete="CASCADE"), primary_key=True)
    Noizzy_id: Mapped[int] = mapped_column(ForeignKey('Noizzy.id', ondelete="CASCADE"))
    visto: Mapped[bool] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'noizzito',
        'inherit_condition': (id == Noizzy.id)
    }

    __table_args__ = (
        CheckConstraint("id != Noizzy_id", name="chk_noAutoComentario"),
    )

    # Relacion "Responde" con Noizzy (1 a N)
    noizzy: Mapped["Noizzy"] = relationship(uselist=False, foreign_keys=[Noizzy_id], primaryjoin="Noizzito.Noizzy_id == Noizzy.id",
        back_populates="noizzitos")
