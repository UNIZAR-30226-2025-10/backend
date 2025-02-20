from sqlalchemy import create_engine
from db import engine  # Importa el motor de la base de datos
from models import Base  # Importa la clase Base que define tus modelos

def create_tables():
    """Crea las tablas en la base de datos."""
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")

if __name__ == "__main__":
    create_tables()
