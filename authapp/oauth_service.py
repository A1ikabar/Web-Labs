# authapp/oauth_service.py
# Сервис для работы с Яндекс OAuth 2.0 (Authorization Code Grant flow)

import requests  # HTTP-библиотека для запросов к Яндекс API
import secrets  # Генерация криптографически стойких случайных значений
import hashlib  # Хеширование для защиты state-токена
from datetime import datetime, timedelta  # Работа со временем
from django.core.cache import cache  # Кеш Django для хранения state (CSRF-защита)
from django.utils import timezone  # Утилиты времени Django
from users.models import User  # Модель пользователя
from authapp.jwt_utils import create_access_token, create_refresh_token  # Генерация JWT
from authapp.utils import hash_password, hash_token  # Хеширование паролей и токенов
from .oauth_config import YandexOAuthConfig  # Конфигурация OAuth (ключи, URL)


class YandexOAuthService:
    """
    Сервис для работы с Яндекс OAuth 2.0.
    Реализует поток Authorization Code Grant вручную.
    
    Этапы потока:
    1. generate_state() + get_authorization_url() — редирект пользователя на Яндекс
    2. exchange_code_for_token() — обмен кода на токен Яндекс
    3. get_user_info() — получение данных пользователя
    4. find_or_create_user() — поиск/создание в локальной БД
    5. create_local_session() — генерация локальных JWT
    """

    @staticmethod
    def generate_state() -> str:
        """
        Генерация уникального state-токена для защиты от CSRF-атак.
        
        Зачем нужен state:
        - Защита от подделки межсайтовых запросов
        - Клиент генерирует state перед редиректом на провайдера
        - Провайдер возвращает state в callback
        - Сервер сверяет полученный state с сохранённым
        
        Механизм:
        1. Генерируем случайную строку (32 байта, URL-safe)
        2. Хешируем state (SHA256) для безопасного хранения в кеше
        3. Сохраняем хеш в кеше на 5 минут (время жизни сессии OAuth)
        """
        # Генерируем случайную строку для state
        state = secrets.token_urlsafe(32)
        # Хешируем state перед сохранением (безопасность)
        state_hash = hashlib.sha256(state.encode()).hexdigest()

        # Сохраняем хеш state в кеше на 5 минут (время из конфига)
        # Ключ формата 'oauth_state:{hash}' для уникальности
        cache.set(f'oauth_state:{state_hash}', state_hash, timeout=YandexOAuthConfig.STATE_EXPIRES_IN)

        return state

    @staticmethod
    def validate_state(state: str) -> bool:
        """
        Проверка валидности state-токена после возврата от провайдера.
        
        Алгоритм:
        1. Хешируем полученный state тем же способом
        2. Ищем хеш в кеше
        3. Если найден — удаляем (одноразовый use) и возвращаем True
        4. Если не найден — возвращаем False (CSRF-атака или истёк)
        """
        # Хешируем полученный state
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        # Пытаемся получить хеш из кеша
        cached_state = cache.get(f'oauth_state:{state_hash}')

        if cached_state:
            # Удаляем state из кеша (одноразовый токен)
            cache.delete(f'oauth_state:{state_hash}')
            return True
        return False

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """
        Формирование URL для редиректа пользователя на Яндекс OAuth.
        
        Параметры URL:
        - response_type=code: запрашиваем код авторизации (не токен)
        - client_id: идентификатор приложения в Яндекс OAuth
        - redirect_uri: куда Яндекс перенаправит после авторизации
        - scope: запрашиваемые права (login:email, login:info)
        - state: CSRF-токен для защиты
        
        Возвращает полный URL для редиректа пользователя.
        """
        # Формируем параметры запроса
        params = {
            'response_type': 'code',  # Authorization Code Grant
            'client_id': YandexOAuthConfig.CLIENT_ID,
            'redirect_uri': YandexOAuthConfig.REDIRECT_URI,
            'scope': YandexOAuthConfig.SCOPE,  # 'login:email login:info'
            'state': state,  # CSRF-токен
        }

        # Собираем query string вручную (ключ=значение&ключ=значение)
        query_string = '&'.join([f'{key}={value}' for key, value in params.items()])
        # Возвращаем полный URL
        return f"{YandexOAuthConfig.AUTHORIZATION_URL}?{query_string}"

    @staticmethod
    def exchange_code_for_token(code: str) -> dict:
        """
        Обмен кода авторизации на access-токен Яндекс.
        
        Этап Authorization Code Grant:
        1. Отправляем POST на https://oauth.yandex.ru/token
        2. Передаём: grant_type, code, client_id, client_secret, redirect_uri
        3. Получаем JSON с access_token Яндекс
        
        Возвращает dict с токеном и метаданными.
        """
        # Данные для POST-запроса
        data = {
            'grant_type': 'authorization_code',  # Тип потока
            'code': code,  # Код авторизации из callback
            'client_id': YandexOAuthConfig.CLIENT_ID,
            'client_secret': YandexOAuthConfig.CLIENT_SECRET,
            'redirect_uri': YandexOAuthConfig.REDIRECT_URI,
        }

        # Отправляем POST-запрос на Яндекс
        response = requests.post(YandexOAuthConfig.TOKEN_URL, data=data)

        # Проверяем статус ответа
        if response.status_code != 200:
            raise ValueError(f"Yandex OAuth error: {response.text}")

        # Возвращаем распаршенный JSON
        return response.json()

    @staticmethod
    def get_user_info(access_token: str) -> dict:
        """
        Получение данных пользователя от Яндекс через OAuth API.
        
        Запрос к https://login.yandex.ru/info возвращает:
        - id: уникальный ID пользователя в Яндекс
        - default_email: основной email
        - emails: список email'ов
        - other данные профиля
        
        Требуется заголовок Authorization: OAuth {token}.
        """
        # Заголовок с токеном доступа
        headers = {'Authorization': f'OAuth {access_token}'}
        # GET-запрос к API Яндекс
        response = requests.get(YandexOAuthConfig.USER_INFO_URL, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"Yandex user info error: {response.text}")

        return response.json()

    @staticmethod
    def find_or_create_user(yandex_info: dict) -> User:
        """
        Поиск или создание пользователя в локальной БД.
        
        Логика:
        1. Ищем по yandex_id (если пользователь уже входил через Яндекс)
        2. Если не найден — ищем по email (привязываем Яндекс к существующему)
        3. Если не найден — создаём нового с случайным паролем
        
        Возвращает объект User.
        """
        # Извлекаем данные из ответа Яндекс
        yandex_id = str(yandex_info.get('id'))  # Уникальный ID в Яндекс
        email = yandex_info.get('default_email') or yandex_info.get('emails', [None])[0]

        # Email обязателен для регистрации
        if not email:
            raise ValueError("Email не получен от Яндекс")

        # Поиск по yandex_id (если уже входил через Яндекс)
        user = User.objects.filter(yandex_id=yandex_id).first()

        if user:
            return user

        # Поиск по email (если есть аккаунт с таким email)
        user = User.objects.filter(email=email).first()

        if user:
            # Привязываем yandex_id к существующему аккаунту
            user.yandex_id = yandex_id
            user.save()
            return user

        # Создание нового пользователя
        # Генерируем случайный пароль (вход через OAuth, пароль не используется)
        random_password = secrets.token_urlsafe(32)
        password_hash, password_salt = hash_password(random_password)

        # Создаём запись в БД
        user = User.objects.create(
            email=email,
            yandex_id=yandex_id,
            password_hash=password_hash,
            password_salt=password_salt,
        )

        return user

    @staticmethod
    def create_local_session(user: User) -> tuple:
        """
        Генерация локальных JWT-токенов после успешного OAuth входа.
        
        Создаёт пару access/refresh токенов, хеширует их
        и сохраняет в БД (аналогично обычному login).
        
        Возвращает кортеж: (access_token, refresh_token).
        """
        # Генерируем JWT-токены через утилиты
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Генерируем соли для безопасного хранения в БД
        access_salt = secrets.token_hex(16)
        refresh_salt = secrets.token_hex(16)

        # Импортируем модель токенов (внутри метода для избежания циклического импорта)
        from users.models import UserToken

        # Сохраняем хеш access-токена в БД
        UserToken.objects.create(
            user=user,
            token_hash=hash_token(access_token, access_salt),
            token_salt=access_salt,
            token_type='access',
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Сохраняем хеш refresh-токена в БД
        UserToken.objects.create(
            user=user,
            token_hash=hash_token(refresh_token, refresh_salt),
            token_salt=refresh_salt,
            token_type='refresh',
            expires_at=timezone.now() + timedelta(days=7),
        )

        return access_token, refresh_token