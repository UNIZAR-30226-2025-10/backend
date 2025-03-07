from db import engine
from models import Base
from sqlalchemy import text

triggers = [
    """
    -- Trigger para evitar ser participante de una Playlist propia
    CREATE TRIGGER trg_participanteNoCreador
    BEFORE INSERT ON Participante
    FOR EACH ROW
    BEGIN
        SELECT CASE
            WHEN (SELECT Oyente_correo FROM Playlist WHERE id = NEW.Playlist_id) = NEW.Oyente_correo
            THEN RAISE (ABORT, 'No se puede insertar, el oyente es el dueño de esta playlist.')
        END;
    END;
    """,
    """
    -- Trigger para evitar ser invitado de una Playlist propia
    CREATE TRIGGER trg_invitadoNoCreador
    BEFORE INSERT ON Invitado
    FOR EACH ROW
    BEGIN
        SELECT CASE
            WHEN (SELECT Oyente_correo FROM Playlist WHERE id = NEW.Playlist_id) = NEW.Oyente_correo
            THEN RAISE (ABORT, 'No se puede insertar, el oyente es el dueño de esta playlist.')
        END;
    END;
    """,
    """
    -- Trigger para evitar ser Featuring en una Cancion propia
    CREATE TRIGGER trg_noAutoFeaturing
    BEFORE INSERT ON Featuring
    FOR EACH ROW
    BEGIN
        SELECT CASE
            WHEN (SELECT Artista_correo FROM Cancion WHERE id = NEW.Cancion_id) = NEW.Artista_correo
            THEN RAISE (ABORT, 'No se puede insertar, el artista es el creador de la cancion.')
        END;
    END;
    """
]

"""Crea las tablas en la BD Turso"""
def create_tables():
    # Borra las tablas del models.py en la base de datos
    Base.metadata.drop_all(engine)
    # Crea las tablas del models.py en la base de datos
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")

    # Crea los triggers en la base de datos
    with engine.connect() as connection:
        for trigger in triggers:
            connection.execute(text(trigger))
        print("Triggers creados exitosamente.")

if __name__ == "__main__":
    create_tables()
