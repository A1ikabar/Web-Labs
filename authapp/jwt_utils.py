import os
import jwt
from datetime import datetime, timedelta, UTC
import uuid

def create_access_token(user_id: str) -> str:
    expiration_minutes = int(os.getenv('JWT_ACCESS_EXPIRATION_MINUTES', '15'))
    payload = {
        'sub': user_id,
        'type': 'access',
        'jti': str(uuid.uuid4()),
        'exp': datetime.now(UTC) + timedelta(minutes=expiration_minutes),
    }
    return jwt.encode(payload, os.getenv('JWT_ACCESS_SECRET'), algorithm='HS256')

def create_refresh_token(user_id: str) -> str:
    expiration_days = int(os.getenv('JWT_REFRESH_EXPIRATION_DAYS', '7'))
    payload = {
        'sub': user_id,
        'type': 'refresh',
        'exp': datetime.now(UTC) + timedelta(days=expiration_days),
    }
    return jwt.encode(payload, os.getenv('JWT_REFRESH_SECRET'), algorithm='HS256')

def decode_access_token(token: str):
    return jwt.decode(token, os.getenv('JWT_ACCESS_SECRET'), algorithms=['HS256'])

def decode_refresh_token(token: str):
    return jwt.decode(token, os.getenv('JWT_REFRESH_SECRET'), algorithms=['HS256'])