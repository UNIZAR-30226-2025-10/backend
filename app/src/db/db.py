from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine
from contextlib import contextmanager
import os

TURSO_URL = os.environ.get("TURSO_URL")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN")

# Verificar que las variables de entorno existen
if not TURSO_URL or not TURSO_TOKEN:
    raise ValueError("Faltan variables de entorno TURSO_URL o TURSO_TOKEN en el archivo .env")

# Crear la URL de conexión con Turso
db_url = URL.create(
    drivername="sqlite+libsql",
    host=TURSO_URL,
    query={"authToken": TURSO_TOKEN, "secure": "true"},
)

# Crear el motor de la base de datos
engine = create_engine(db_url, connect_args={"check_same_thread": False}, echo=True)

# Crear una sesión reutilizable
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

'''Obtiene una sesion para conectarse a la BD'''
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db  # Devuelve la sesión para que la use el endpoint
    finally:
        db.close()  # Asegura que la sesión se cierre correctamente
