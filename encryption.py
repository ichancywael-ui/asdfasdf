from cryptography.fernet import Fernet
import os

key = os.getenv("SECRET_KEY").encode()

cipher = Fernet(key)

def encrypt_password(password: str) -> str:
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    return cipher.decrypt(encrypted_password.encode()).decode()