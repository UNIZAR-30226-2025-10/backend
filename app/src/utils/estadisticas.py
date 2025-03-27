from db.models import EsParteDePlaylist, Cancion, Playlist
from sqlalchemy import select

def estadisticas_song(cancion_entry, db):    
    stmt_n_playlists = select(EsParteDePlaylist.Cancion_id).where(
        EsParteDePlaylist.Cancion_id == cancion_entry.id
    )
    n_playlists = len(db.scalars(stmt_n_playlists).all())

    stmt_favs = (
        select(EsParteDePlaylist.Cancion_id)
        .join(Playlist, EsParteDePlaylist.Playlist_id == Playlist.id)
        .where(
            EsParteDePlaylist.Cancion_id == cancion_entry.id,
            Playlist.nombre == "Favoritos"
        )
    )
    favs = len(db.scalars(stmt_favs).all())
    
    return n_playlists, favs