import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import URL

# Cargar las variables de "".env" como variables de entorno
load_dotenv(os.path.join(os.path.dirname(__file__), "/backend/.env"))

TURSO_URL = os.environ.get("TURSO_URL")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN")

# Crear la URL de conexión con Turso
db_url = URL.create(
    drivername="sqlite+libsql",
    host=TURSO_URL,
    query={"authToken": TURSO_TOKEN, "secure": "true"},
)

engine = create_engine(db_url, connect_args={"check_same_thread": False}, echo=True)

# Crear una sesión reutilizable
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

'''Obtiene una sesion para conectarse a la BD'''
def get_db() -> Session:
    return SessionLocal()