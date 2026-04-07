import requests
import secrets
import hashlib
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from urllib.parse import urlencode

from authapp.jwt_utils import create_access_token, create_refresh_token
from authapp.utils import hash_password, hash_token
from users.mongo_service import (
    find_user_by_yandex_id,
    find_user_by_email,
    create_user,
    update_user,
)
from users.token_mongo_service import create_user_token
from .oauth_config import YandexOAuthConfig

class YandexOAuthService:
    @staticmethod
    def generate_state() -> str:
        state = secrets.token_urlsafe(32)
        state_hash = hashlib.sha256(state.encode()).hexdigest()

        cache.set(
            f'oauth_state:{state_hash}',
            state_hash,
            timeout=YandexOAuthConfig.STATE_EXPIRES_IN
        )

        return state

    @staticmethod
    def validate_state(state: str) -> bool:
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        cached_state = cache.get(f'oauth_state:{state_hash}')

        if cached_state:
            cache.delete(f'oauth_state:{state_hash}')
            return True
        return False

    @staticmethod
    def get_authorization_url(state: str) -> str:
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
    def find_or_create_user(yandex_info: dict) -> dict:
        yandex_id = str(yandex_info.get('id'))
        email = yandex_info.get('default_email')

        if not email:
            emails = yandex_info.get('emails') or []
            email = emails[0] if emails else None

        if not email:
            raise ValueError("Email не получен от Яндекс")

        user = find_user_by_yandex_id(yandex_id)
        if user:
            return user

        user = find_user_by_email(email)
        if user:
            updated_user = update_user(str(user["_id"]), {"yandex_id": yandex_id})
            return updated_user

        random_password = secrets.token_urlsafe(32)
        password_hash, password_salt = hash_password(random_password)

        user = create_user(
            email=email,
            password_hash=password_hash,
            password_salt=password_salt,
            yandex_id=yandex_id,
        )

        return user

    @staticmethod
    def create_local_session(user: dict) -> tuple:
        user_id = str(user["_id"])

        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        access_salt = secrets.token_hex(16)
        refresh_salt = secrets.token_hex(16)

        create_user_token(
            user_id=user_id,
            token_hash=hash_token(access_token, access_salt),
                        token_salt=access_salt,
            token_type='access',
            expires_at=timezone.now() + timedelta(minutes=15),
            revoked=False,
        )

        create_user_token(
            user_id=user_id,
            token_hash=hash_token(refresh_token, refresh_salt),
            token_salt=refresh_salt,
            token_type='refresh',
            expires_at=timezone.now() + timedelta(days=7),
            revoked=False,
        )

        return access_token, refresh_token