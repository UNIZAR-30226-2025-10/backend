import random

'''Devuelve un codigo de verificacion de 6 cifras'''
def new_code() -> str:
    return str(random.randint(0, 999999)).zfill(6)  # Asegura 6 dígitos con ceros a la izquierda
