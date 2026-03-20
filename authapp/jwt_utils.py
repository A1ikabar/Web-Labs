# os — чтение секретных ключей из переменных окружения
# jwt — библиотека PyJWT для работы с JSON Web Tokens
# datetime — работа со временем истечения токенов
import os
import jwt
from datetime import datetime, timedelta, UTC


def create_access_token(user_id: str) -> str:
    """
    Создание JWT access-токена.
    Access-токен имеет короткое время жизни (15 минут по умолчанию).
    Используется для доступа к защищённым ресурсам.
    
    Структура JWT payload:
    - sub (subject): ID пользователя
    - type: тип токена ('access')
    - exp (expiration): время истечения
    """
    # Читаем время жизни токена из .env (по умолчанию 15 минут)
    expiration_minutes = int(os.getenv('JWT_ACCESS_EXPIRATION_MINUTES', '15'))
    # Формируем payload — данные, которые будут зашиты в токен
    payload = {
        'sub': user_id,  # ID пользователя (subject)
        'type': 'access',  # Тип токена для проверки
        'exp': datetime.now(UTC) + timedelta(minutes=expiration_minutes),  # Время истечения
    }
    # Подписываем токен секретным ключом алгоритмом HS256 (HMAC-SHA256)
    return jwt.encode(payload, os.getenv('JWT_ACCESS_SECRET'), algorithm='HS256')


def create_refresh_token(user_id: str) -> str:
    """
    Создание JWT refresh-токена.
    Refresh-токен имеет длительное время жизни (7 дней по умолчанию).
    Используется для получения новой пары access/refresh токенов.
    
    Refresh-токены хранятся в БД и могут быть отозваны.
    """
    # Читаем время жизни токена из .env (по умолчанию 7 дней)
    expiration_days = int(os.getenv('JWT_REFRESH_EXPIRATION_DAYS', '7'))
    # Формируем payload
    payload = {
        'sub': user_id,
        'type': 'refresh',  # Тип токена
        'exp': datetime.now(UTC) + timedelta(days=expiration_days),
    }
    # Подписываем другим секретным ключом (для разделения access/refresh)
    return jwt.encode(payload, os.getenv('JWT_REFRESH_SECRET'), algorithm='HS256')


def decode_access_token(token: str):
    """
    Декодирование и проверка access-токена.
    Проверяет подпись и срок действия.
    Бросает исключение, если токен невалиден или истёк.
    """
    # jwt.decode автоматически проверяет подпись и exp claim
    return jwt.decode(token, os.getenv('JWT_ACCESS_SECRET'), algorithms=['HS256'])


def decode_refresh_token(token: str):
    """
    Декодирование и проверка refresh-токена.
    Проверяет подпись и срок действия.
    Бросает исключение, если токен невалиден или истёк.
    """
    # Используем отдельный секрет для refresh-токенов
    return jwt.decode(token, os.getenv('JWT_REFRESH_SECRET'), algorithms=['HS256'])