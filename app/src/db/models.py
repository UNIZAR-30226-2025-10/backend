from datetime import datetime
from datetime import date
from datetime import time
from .triggers import trg_estaInvitado, trg_eliminarInvitado, trg_noParticipante #, trg_10Playlists, trg_50Canciones
from sqlalchemy import Table, Column, ForeignKey, CheckConstraint, event, ForeignKeyConstraint, String
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase, validates

class Base(DeclarativeBase):
    pass

# Tabla intermedia para 'Sigue'
sigue_table = Table(
    "Sigue", Base.metadata,
    Column("Seguidor_correo", String, ForeignKey("Oyente.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    Column("Seguido_correo", String, ForeignKey("Oyente.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    CheckConstraint("Seguidor_correo != Seguido_correo", name="chk_noAutoSeguimiento")
)

# Tabla intermedia para 'Participante'
participante_table = Table(
    "Participante", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_id", String, ForeignKey("Playlist.id", ondelete="CASCADE"), primary_key=True),

    CheckConstraint("Oyente_correo != Playlist_Oyente_correo", name="chk_participanteNoCreador")
)
event.listen(participante_table, "after_create", trg_estaInvitado)
event.listen(participante_table, "after_create", trg_eliminarInvitado)

# Tabla intermedia para 'Invitado'
invitado_table = Table(
    "Invitado", Base.metadata,
    Column("Oyente_correo", String, ForeignKey("Oyente.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    Column("Playlist_id", String, ForeignKey("Playlist.id", ondelete="CASCADE"), primary_key=True),

    CheckConstraint("Oyente_correo != Playlist_Oyente_correo", name="chk_invitadoNoCreador")
)
event.listen(invitado_table, "after_create", trg_noParticipante)

# Tabla intermedia para 'HistorialColeccion'
class HistorialColeccion(Base):
    __tablename__ = "HistorialColeccion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.Usuario_correo"), primary_key=True)
    Coleccion_id: Mapped[str] = mapped_column(ForeignKey("Coleccion.id"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    # Relaciones con Usuario y Playlist
    oyente: Mapped["Oyente"] = relationship(back_populates="historialColeccion")
    coleccion: Mapped["Coleccion"] = relationship(back_populates="historialColeccion")
# event.listen(HistorialPlaylist, "after_insert", trg_10Playlists)

# Tabla intermedia para 'HistorialCancion'
class HistorialCancion(Base):
    __tablename__ = "HistorialCancion"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.Usuario_correo"), primary_key=True)
    Cancion_id: Mapped[str] = mapped_column(ForeignKey("Cancion.id"), primary_key=True)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)

    oyente: Mapped["Oyente"] = relationship(back_populates="historialCancion")
    cancion: Mapped["Cancion"] = relationship(back_populates="historialCancion")
# event.listen(HistorialCancion, "after_insert", trg_50Canciones)

# Tabla intermedia para "EstaEscuchando"
class EstaEscuchando(Base):
    __tablename__ = "EstaEscuchando"

    Oyente_correo: Mapped[str] = mapped_column(ForeignKey("Oyente.Usuario_correo"), primary_key=True)
    Cancion_id: Mapped[str] = mapped_column(ForeignKey("Cancion.id"), nullable=False)
    minuto: Mapped[int] = mapped_column(nullable=False)
    segundo: Mapped[int] = mapped_column(nullable=False)

    # Restricciones a nivel de BD
    __table_args__ = (
        CheckConstraint('minuto BETWEEN 0 AND 60', name='chk_minuto'),
        CheckConstraint('segundo BETWEEN 0 AND 60', name='chk_segundo'),
    )

    # Restricciones a nivel de Python
    @validates("minuto")
    def validate_minuto(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Minuto debe estar entre 0 y 60")
        return value
    
    @validates("segundo")
    def validate_segundo(self, key, value):
        if not (0 <= value <= 60):
            raise ValueError("Segundo debe estar entre 0 y 60")
        return value

    oyente: Mapped["Oyente"] = relationship(back_populates="estaEscuchando")
    cancion: Mapped["Cancion"] = relationship(back_populates="estaEscuchando")

# Tabla intermedia para "Like"
like_table = Table(
    "Like", Base.metadata,
    Column("Oyente_correo", ForeignKey("Oyente.Usuario_correo", ondelete="CASCADE"), primary_key=True),
    Column("Noizzy_id", ForeignKey("Noizzy.id", ondelete="CASCADE"), primary_key=True)
)

# Tabla intermedia para "EsParteDePlaylist"
class EsParteDePlaylist(Base):
    __tablename__ = "EsParteDePlaylist"

    Cancion_id: Mapped[str] = mapped_column(ForeignKey("Cancion.id"), primary_key=True)
    Playlist_id: Mapped[str] = mapped_column(ForeignKey("Playlist.id"), primary_key=True)
    puesto: Mapped[int] = mapped_column(unique=True, nullable=False)

    cancion: Mapped["Cancion"] = relationship(back_populates="esParteDePlaylist")
    playlist: Mapped["Playlist"] = relationship(back_populates="esParteDePlaylist")

# Tabla intermedia para "Pertenece"
pertenece_table = Table(
    "Pertenece", Base.metadata,
    Column("Cancion_id", ForeignKey("Cancion.id", ondelte="CASCADE"), primary_key=True),
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

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',  
        'polymorphic_on': tipo  
    }

    # Constraint para tipo
    __table_args__ = (
        CheckConstraint("tipo IN ('admin', 'pendiente', 'valido', 'oyente', 'artista')", 
                        name="chk_tipo_valido"),)
    
    # Convertir a diccionario para devolver en formato JSON
    def to_dict(self):
        return {
            "correo": self.correo,
            "nombreUsuario": self.nombreUsuario
        }

# Entidad Admin
class Admin(Usuario):
    __tablename__ = 'Admin'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }

# Entidad Pendiente
class Pendiente(Usuario):
    __tablename__ = 'Pendiente'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo'), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'pendiente',
    }

# Entidad Valido
class Valido(Usuario):
    __tablename__ = 'Valido'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)
    codigo: Mapped[str] = mapped_column(nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'valido',
    }

# Entidad Oyente
class Oyente(Usuario):
    __tablename__ = "Oyente"
    
    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Usuario.correo', ondelete="CASCADE"), primary_key=True)
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

    # Restricción en volumen (0-100) a nivel de Python
    @validates("volumen")
    def validate_volumen(self, key, value):
        if not (0 <= value <= 100):
            raise ValueError("Volumen debe estar entre 0 y 100")
        return value
    
    # Relacion "CreaPlaylist" con Playlist (1 a N)
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="oyente", cascade="all, delete-orphan")

    # Relacion "Seguidos" y "Seguidores"
    seguidos: Mapped[list["Oyente"]] = relationship(
        secondary=sigue_table,
        primaryjoin=Usuario_correo == sigue_table.c.Seguidor_correo,  # El usuario actual es el seguidor
        secondaryjoin=Usuario_correo == sigue_table.c.Seguido_correo,  # Se une con los usuarios seguidos
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
    
    # Relacion con tabla intermedia "EstaEscuchando"
    estaEscuchando: Mapped["EstaEscuchando"] = relationship(uselist=False, back_populates="oyente",
        cascade="all, delete-orphan")
        
    # Relacion "Postea" con Noizzy (1 a N)
    noizzys: Mapped[list["Noizzy"]] = relationship(back_populates="oyente", cascade="all, delete-orphan")
    
    # Relacion "Like" con Noizzy (N a M)
    liked: Mapped[list["Noizzy"]] = relationship(secondary=like_table, back_populates="likes",
        passive_deletes=True)

    # Convertir a diccionario para devolver en formato JSON
    def to_dict(self):
        return {
            "correo": self.correo,
            "nombreUsuario": self.nombreUsuario,
            "fotoPerfil": self.fotoPerfil,
            "volumen": self.volumen
        }

class Artista(Oyente):
    __tablename__ = 'Artista'

    Usuario_correo: Mapped[str] = mapped_column(ForeignKey('Oyente.Usuario_correo', ondelete="CASCADE"), primary_key=True)
    nombreArtistico: Mapped[str] = mapped_column(nullable=False)
    biografia: Mapped[str] = mapped_column(nullable=True)

    # Relacion "CreaAlbum" con Album (1 a N)
    albumes: Mapped[list["Album"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    # Relacion "CreaCancion" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="artista", cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'artista',
    }

    # Convertir a diccionario para devolver en formato JSON
    def to_dict(self):
        return {
            "correo": self.Usuario_correo,
            "nombreArtistico": self.nombreArtistico,
            "biografia": self.biografia,
            "nombreUsuario": self.nombreUsuario,
            "fotoPerfil": self.fotoPerfil,
            "volumen": self.volumen
        }

class Coleccion(Base):
    __tablename__ = 'Coleccion'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(nullable=False)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)

    # Relacion directa con la tabla intermedia "HistorialColeccion" (N a M)
    historialColeccion: Mapped[list["HistorialColeccion"]] = relationship(back_populates="playlist",
        cascade="all, delete")

class Album(Coleccion):
    __tablename__ = 'Album'

    id: Mapped[int] = mapped_column(ForeignKey('Coleccion.id'), primary_key=True)
    nombre: Mapped[str] = mapped_column(nullable=False)
    Artista_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), nullable=False)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(nullable=False)

    # Relacion "CreaAlbum" con Artista (1 a N)
    artista: Mapped["Artista"] = relationship(uselist=False, back_populates="albumes")

    # Relacion "EsParteDeAlbum" con Cancion (1 a N)
    canciones: Mapped[list["Cancion"]] = relationship(back_populates="album", cascade="all, delete-orphan",
        order_by="Cancion.puesto")

class Playlist(Coleccion):
    __tablename__ = 'Playlist'

    id: Mapped[int] = mapped_column(ForeignKey('Coleccion.id'), primary_key=True)
    nombre: Mapped[str] = mapped_column(nullable=False)
    Oyente_correo: Mapped[str] = mapped_column(ForeignKey('Oyente.Usuario_correo'), nullable=False)
    fotoPortada: Mapped[str] = mapped_column(nullable=False)
    privacidad: Mapped[bool] = mapped_column(nullable=False)

    # Relacion con tabla intermedia "EsParteDePlaylist"
    esParteDePlaylist: Mapped[list["EsParteDePlaylist"]] = relationship(back_populates="playlist",
        cascade="all, delete-orphan")

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Participantes"
    participantes: Mapped[list["Oyente"]] = relationship(secondary=participante_table, back_populates="participante",
        passive_deletes=True)

    # Relacion con "Usuario" (N:M) a traves de la la tabla intermedia "Invitado"
    invitados: Mapped[list["Oyente"]] = relationship(secondary=invitado_table, back_populates="invitado",
        passive_deletes=True)

    # Relacion "CreaPlaylist" con Usuario (1 a N)
    oyente: Mapped["Oyente"] = relationship(uselist=False, back_populates="playlists")
    
# Entidad Cancion
class Cancion(Base):
    __tablename__ = "Cancion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Artista_correo: Mapped[str] = mapped_column(ForeignKey('Artista.Usuario_correo'), nullable=False)
    nombre: Mapped[str] = mapped_column(nullable=False)
    duracion: Mapped[int] = mapped_column(nullable=False)   # Duracion en segundos
    audio: Mapped[str] = mapped_column(nullable=False)
    fechaPublicacion: Mapped[date] = mapped_column(nullable=False)
    reproducciones: Mapped[int] = mapped_column(nullable=False)
    Album_Artista_correo:  Mapped[str] = mapped_column(nullable=False)
    Album_nombre: Mapped[str] = mapped_column(nullable=False)
    puesto: Mapped[int] = mapped_column(unique=True, nullable=False)

    __table_args__ = (
        CheckConstraint("Artista_correo == Album_Artista_correo", name="chk_cancionAlbum"),
        ForeignKeyConstraint(
            ["Album_nombre", "Album_Artista_correo"], ["Album.nombre", "Album.Artista_correo"]),
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
    
    # Relacion "EstaEscuchando" con Usuario (1 a N)
    estaEscuchando: Mapped["EstaEscuchando"] = relationship(uselist=False, back_populates="cancion",
        cascade="all, delete-orphan")

    # Convertir a diccionario para devolver en formato JSON
    def to_dict(self):
        return {
            "artista": self.Artista_correo,
            "nombre": self.nombre,
            "duracion": self.duracion,
            "audio": self.audio,
            "fechaPublicacion": self.fechaPublicacion,
            "reproducciones": self.reproducciones,
            "album":self.Album_nombre,
            "puesto":self.puesto,
            "fotoPortada":self.album.fotoPortada
        }

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
    Oyente_correo: Mapped[str] = mapped_column(ForeignKey('Oyente.Usuario_correo'), nullable=False)
    fechaHora: Mapped[datetime] = mapped_column(nullable=False)
    texto: Mapped[str] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(nullable=False)
    Cancion_id: Mapped[str] = mapped_column(ForeignKey('Cancion.id'), nullable=False)

    # Parametros de herencia
    __mapper_args__ = {
        'polymorphic_identity': 'noizzy',  
        'polymorphic_on': tipo  
    }

    # Relacion "Postea" con Usuario (1 a N)
    oyente: Mapped["Oyente"] = relationship(uselist=False, back_populates="noizzys")

    # Relacion "Responde" con Noizzito (1 a N)
    noizzitos: Mapped[list["Noizzito"]] = relationship(back_populates="noizzy", foreign_keys="[Noizzito.Noizzy_id]", 
        cascade="all, delete-orphan")

    # Relacion "Referencia" con Cancion (1 a N)
    cancion: Mapped["Cancion"] = relationship(uselist=False, back_populates="noizzys")
    
    # Relacion "Like" con Usuario (N a M)
    likes: Mapped[list["Oyente"]] = relationship(secondary=like_table, back_populates="liked",
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
        CheckConstraint("id != Noizzy_id", name="chk_noAutoComentario"),
    )

    # Relacion "Responde" con Noizzy (1 a N)
    noizzy: Mapped["Noizzy"] = relationship(uselist=False, foreign_keys=[Noizzy_id], primaryjoin="Noizzito.Noizzy_id == Noizzy.id",
        back_populates="noizzitos")
