import bcrypt

"""Genera un hash seguro para la contraseña con bcrypt"""
def hash(password: str) -> str:
    salt = bcrypt.gensalt()  # Generar un salt automáticamente
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()  # Convertir a str para guardarlo en la DB

"""Verifica si la contraseña ingresada coincide con el hash almacenado"""
def verify(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())
