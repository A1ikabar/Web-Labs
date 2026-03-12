import bcrypt
import secrets
import hashlib

def hash_password(password: str) -> tuple[str, str]:
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    return password_hash, salt.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_token_salt() -> str:
    return secrets.token_hex(16)

def hash_token(token: str, salt: str) -> str:
    return hashlib.sha256(f'{token}{salt}'.encode('utf-8')).hexdigest()