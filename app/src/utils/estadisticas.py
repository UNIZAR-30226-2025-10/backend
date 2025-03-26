from db.models import EsParteDePlaylist, Cancion, Playlist
from sqlalchemy import select, exists, and_

def estadisticas_song(cancion_entry, db):    
    n_playlists = db.get(EsParteDePlaylist).filter_by(Cancion_id=cancion_entry.id).count()
            
    favs = db.query(EsParteDePlaylist).join(Playlist).filter(
        EsParteDePlaylist.Cancion_id == cancion_entry.id, Playlist.nombre == "Favoritos"
    ).count()
    
    return n_playlists, favs