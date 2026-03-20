# authapp/oauth_config.py
# Конфигурация OAuth для Яндекс (ключи, эндпоинты, настройки)

import os  # Чтение переменных окружения
from dotenv import load_dotenv  # Загрузка .env файла

# Загружаем переменные окружения из .env файла
load_dotenv()


class YandexOAuthConfig:
    """
    Класс конфигурации OAuth для Яндекс.
    Содержит все необходимые параметры для работы с Яндекс OAuth 2.0.
    
    Данные берутутся из .env файла:
    - YANDEX_CLIENT_ID: идентификатор приложения в Яндекс OAuth Console
    - YANDEX_CLIENT_SECRET: секретный ключ приложения
    - YANDEX_REDIRECT_URI: URL callback'а (куда Яндекс перенаправит после авторизации)
    """

    # Идентификатор приложения (выдаётся в консоли разработчика Яндекс)
    CLIENT_ID = os.getenv('YANDEX_CLIENT_ID')
    
    # Секретный ключ приложения (хранить в тайне, не коммитить в git)
    CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET')
    
    # Redirect URI — должен совпадать с настроенным в Яндекс OAuth Console
    # По умолчанию: http://localhost:8000/auth/oauth/yandex/callback
    REDIRECT_URI = os.getenv('YANDEX_REDIRECT_URI', 'http://localhost:8000/auth/oauth/yandex/callback')

    # Эндпоинты Яндекс OAuth API
    # URL для редиректа пользователя на авторизацию
    AUTHORIZATION_URL = 'https://oauth.yandex.ru/authorize'
    # URL для обмена кода авторизации на access-токен
    TOKEN_URL = 'https://oauth.yandex.ru/token'
    # URL для получения данных пользователя по токену
    USER_INFO_URL = 'https://login.yandex.ru/info'

    # Запрашиваемые права (scope)
    # login:email — доступ к email пользователя
    # login:info — доступ к основной информации профиля
    SCOPE = 'login:email login:info'

    # Время жизни state-токена в секундах (5 минут)
    # State используется для CSRF-защиты и должен быть одноразовым
    STATE_EXPIRES_IN = 300