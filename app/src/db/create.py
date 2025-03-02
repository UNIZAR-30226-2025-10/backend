from db import engine
from models import Base

"""Crea las tablas en la BD Turso"""
def create_tables():
    #Borra las tablas en la base de datos
    Base.metadata.drop_all(engine)
    #Crea las tablas en la base de datos
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")

if __name__ == "__main__":
    create_tables()
