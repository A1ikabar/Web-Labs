# authapp/oauth_service.py

import requests
import secrets
import hashlib
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from users.models import User
from authapp.jwt_utils import create_access_token, create_refresh_token
from authapp.utils import hash_password, hash_token
from .oauth_config import YandexOAuthConfig
from urllib.parse import urlencode

class YandexOAuthService:
    """Сервис для работы с Яндекс OAuth"""
    
    @staticmethod
    def generate_state() -> str:
        """Генерация уникального state-токена для защиты от CSRF"""
        state = secrets.token_urlsafe(32)
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        
        # Сохраняем хеш state в кеше на 5 минут
        cache.set(f'oauth_state:{state_hash}', state_hash, timeout=YandexOAuthConfig.STATE_EXPIRES_IN)
        
        return state
    
    @staticmethod
    def validate_state(state: str) -> bool:
        """Проверка валидности state-токена"""
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        cached_state = cache.get(f'oauth_state:{state_hash}')
        
        if cached_state:
            cache.delete(f'oauth_state:{state_hash}')  # Одноразовый use
            return True
        return False
    
    @staticmethod
    def get_authorization_url(state: str) -> str:
        """Формирование URL для редиректа на Яндекс"""
        params = {
            'response_type': 'code',
            'client_id': YandexOAuthConfig.CLIENT_ID,
            'redirect_uri': YandexOAuthConfig.REDIRECT_URI,
            'scope': YandexOAuthConfig.SCOPE,
            'state': state,
        }
        query_string = urlencode(params)
        return f"{YandexOAuthConfig.AUTHORIZATION_URL}?{query_string}"
    
    @staticmethod
    def exchange_code_for_token(code: str) -> dict:
        """Обмен кода авторизации на access-токен Яндекс"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': YandexOAuthConfig.CLIENT_ID,
            'client_secret': YandexOAuthConfig.CLIENT_SECRET,
            'redirect_uri': YandexOAuthConfig.REDIRECT_URI,
        }
        
        response = requests.post(YandexOAuthConfig.TOKEN_URL, data=data)
        
        if response.status_code != 200:
            raise ValueError(f"Yandex OAuth error: {response.text}")
        
        return response.json()
    
    @staticmethod
    def get_user_info(access_token: str) -> dict:
        """Получение данных пользователя от Яндекс"""
        headers = {'Authorization': f'OAuth {access_token}'}
        response = requests.get(
            YandexOAuthConfig.USER_INFO_URL,
            headers=headers,
            params={'format': 'json'},
            timeout=10
        )
        
        if response.status_code != 200:
            raise ValueError(f"Yandex user info error: {response.text}")
        
        return response.json()
    
    @staticmethod
    def find_or_create_user(yandex_info: dict) -> User:
        """Поиск или создание пользователя в локальной БД"""
        yandex_id = str(yandex_info.get('id'))
        email = yandex_info.get('default_email')
        
        if not email:
            emails = yandex_info.get('emails') or []
            email = emails[0] if emails else None
        
        if not email:
            raise ValueError("Email не получен от Яндекс")
        
        # ✅ Поиск по yandex_id
        user = User.objects.filter(yandex_id=yandex_id).first()
        
        if user:
            return user
        
        # ✅ Поиск по email (если уже есть аккаунт)
        user = User.objects.filter(email=email).first()
        
        if user:
            # Привязываем yandex_id к существующему аккаунту
            user.yandex_id = yandex_id
            user.save()
            return user
        
        # ✅ Создание нового пользователя
        # Генерируем случайный пароль (вход через OAuth, пароль не нужен)
        random_password = secrets.token_urlsafe(32)
        password_hash, password_salt = hash_password(random_password)
        
        user = User.objects.create(
            email=email,
            yandex_id=yandex_id,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        
        return user
    
    @staticmethod
    def create_local_session(user: User) -> tuple:
        """Генерация локальных JWT токенов"""
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        
        # Сохраняем хеши токенов в БД
        from users.models import UserToken
        
        access_salt = secrets.token_hex(16)
        refresh_salt = secrets.token_hex(16)
        
        UserToken.objects.create(
            user=user,
            token_hash=hash_token(access_token, access_salt),
            token_salt=access_salt,
            token_type='access',
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        
        UserToken.objects.create(
            user=user,
            token_hash=hash_token(refresh_token, refresh_salt),
            token_salt=refresh_salt,
            token_type='refresh',
            expires_at=timezone.now() + timedelta(days=7),
        )
        
        return access_token, refresh_token