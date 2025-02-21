from sqlalchemy.schema import DDL
from sqlalchemy import event

# Trigger para evitar insertar en Participante sin estar en Invitado
trg_estaInvitado = DDL("""
CREATE TRIGGER IF NOT EXISTS trg_estaInvitado
BEFORE INSERT ON Participante
FOR EACH ROW
WHEN (SELECT COUNT(*) FROM Invitado 
      WHERE Usuario_correo = NEW.Usuario_correo 
      AND Playlist_nombre = NEW.Playlist_nombre 
      AND Playlist_Usuario_correo = NEW.Playlist_Usuario_correo) = 0
BEGIN
    SELECT RAISE(ABORT, 'El usuario debe estar en Invitado antes de ser Participante');
END;
""")

# Trigger para eliminar de Invitado después de insertar en Participante
trg_eliminarInvitado = DDL("""
CREATE TRIGGER IF NOT EXISTS trg_eliminarInvitado
AFTER INSERT ON Participante
FOR EACH ROW
BEGIN
    DELETE FROM Invitado
    WHERE Usuario_correo = NEW.Usuario_correo
    AND Playlist_nombre = NEW.Playlist_nombre
    AND Playlist_Usuario_correo = NEW.Playlist_Usuario_correo;
END;
""")

# Trigger para evitar insertar en Invitado estando en Participante
trg_noParticipante = DDL("""
CREATE TRIGGER IF NOT EXISTS trg_noParticipante
BEFORE INSERT ON Invitado
FOR EACH ROW
WHEN (SELECT COUNT(*) FROM Participante 
      WHERE Usuario_correo = NEW.Usuario_correo 
      AND Playlist_nombre = NEW.Playlist_nombre 
      AND Playlist_Usuario_correo = NEW.Playlist_Usuario_correo) = 1
BEGIN
    SELECT RAISE(ABORT, 'El usuario ya es Participante no puede volver a ser Invitado');
END;
""")

# Trigger para mantener el historial de playlists a 10 playlists
trg_10Playlists = DDL("""
CREATE TRIGGER trg_10Playlists
AFTER INSERT ON HistorialPlaylist
FOR EACH ROW
BEGIN
    -- Si el usuario tiene más de 10 registros en su historial, eliminar el más antiguo
    DELETE FROM HistorialPlaylist
    WHERE Usuario_correo = NEW.Usuario_correo
    AND fechaHora = (
        SELECT MIN(fechaHora) FROM HistorialPlaylist
        WHERE Usuario_correo = NEW.Usuario_correo
    )
    -- Solo eliminar si el usuario tiene más de 10 registros
    AND (SELECT COUNT(*) FROM HistorialPlaylist WHERE Usuario_correo = NEW.Usuario_correo) > 10;
END;
""")

# Trigger para mantener el historial de canciones a 50 canciones
trg_50_Canciones = DDL("""
CREATE TRIGGER trg_50Canciones
AFTER INSERT ON HistorialCancion
FOR EACH ROW
BEGIN
    -- Si el usuario tiene más de 50 registros en su historial, eliminar el más antiguo
    DELETE FROM HistorialCancion
    WHERE Usuario_correo = NEW.Usuario_correo
    AND fechaHora = (
        SELECT MIN(fechaHora) FROM HistorialCancion
        WHERE Usuario_correo = NEW.Usuario_correo
    )
    -- Solo eliminar si el usuario tiene más de 50 registros
    AND (SELECT COUNT(*) FROM HistorialCancion WHERE Usuario_correo = NEW.Usuario_correo) > 50;
END;
""")