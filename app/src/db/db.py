from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Cargar las variables de "".env" como variables de entorno
load_dotenv(os.path.join(os.path.dirname(__file__), "/backend/.env"))

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
def get_db():
    db = SessionLocal()
    yield db  # Devuelve la sesión para que la use el endpoint