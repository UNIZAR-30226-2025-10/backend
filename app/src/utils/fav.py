from db.models import EsParteDePlaylist, Playlist
from sqlalchemy import select, exists, and_

"Devuelve si una cancion esta o no en la lista de Favoritos de un usuario"
def fav(id, correo, db):
    stmt_fav = select(EsParteDePlaylist.Cancion_id).join(Playlist
        ).where(and_(
            Playlist.nombre == "Favoritos",
            Playlist.Oyente_correo == correo, 
            EsParteDePlaylist.Cancion_id == id
        )
    )
    return db.execute(stmt_fav).scalar() is not None