from db.models import EsParteDePlaylist, Playlist
from sqlalchemy import select, exists, and_

"Devuelve si una cancion esta o no en la lista de Favoritos de un usuario"
def fav(id, correo, db):
    stmt = select(exists().where(and_(
        EsParteDePlaylist.Cancion_id == id,
        EsParteDePlaylist.Playlist_id == Playlist.id,
        Playlist.nombre == "Favoritos",
        Playlist.Oyente_correo == correo
    )))
    return db.scalar(stmt)