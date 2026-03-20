# Импорты: DTO для передачи данных, модели пользователей и токенов,
# утилиты для хеширования и работы с JWT
from authapp import dto
from users.models import User
from authapp.utils import hash_password
from authapp.utils import verify_password, generate_token_salt, hash_token
from authapp.jwt_utils import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from users.models import UserToken
from django.utils import timezone
from datetime import timedelta


def register_user(dto):
    """
    Регистрация нового пользователя.
    Проверяет существование пользователя по email, хеширует пароль с солью,
    создаёт запись в БД и возвращает объект пользователя.
    """
    # Проверяем, не занят ли email другим пользователем
    existing_user = User.objects.filter(email=dto.email).first()
    if existing_user:
        raise ValueError("user with this email already exists")

    # Хешируем пароль с уникальной солью (bcrypt)
    password_hash, password_salt = hash_password(dto.password)

    # Создаём новую запись пользователя в БД
    user = User.objects.create(
        email=dto.email,
        password_hash=password_hash,
        password_salt=password_salt,
    )

    return user


def login_user(email: str, password: str):
    """
    Аутентификация пользователя по email и паролю.
    Проверяет учётные данные, генерирует пару JWT-токенов (access + refresh),
    хеширует их и сохраняет в БД для возможности отзыва сессий.
    Возвращает пользователя и оба токена.
    """
    # Ищем пользователя по email (исключая мягко удалённые записи)
    try:
        user = User.objects.get(email=email, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("invalid email or password")

    # Проверяем пароль: сверяем хеш введённого пароля с хешем в БД
    if not verify_password(password, user.password_hash):
        raise ValueError("invalid email or password")

    # Генерируем JWT-токены: access (короткоживущий) и refresh (долгоживущий)
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # Генерируем уникальную соль для каждого токена (для безопасного хранения в БД)
    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    # Вычисляем время истечения токенов
    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    # Сохраняем хеш access-токена в БД (не сам токен, а его хеш с солью)
    UserToken.objects.create(
        user=user,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

    # Сохраняем хеш refresh-токена в БД
    UserToken.objects.create(
        user=user,
        token_hash=hash_token(refresh_token, refresh_salt),
        token_salt=refresh_salt,
        token_type="refresh",
        expires_at=refresh_expiration,
        revoked=False,
    )

    return user, access_token, refresh_token


def get_current_user_from_access_token(access_token: str):
    """
    Извлекает и валидирует пользователя из access-токена.
    Проверяет подпись JWT, тип токена, существование пользователя,
    а также сверяет хеш токена с записью в БД (для отзыва сессий).
    """
    # Декодируем JWT и проверяем подпись
    try:
        payload = decode_access_token(access_token)
    except Exception:
        raise ValueError("invalid or expired access token")

    # Убеждаемся, что токен именно access-типа (не refresh)
    if payload.get("type") != "access":
        raise ValueError("invalid token type")

    # Извлекаем ID пользователя из claims токена (поле 'sub' = subject)
    user_id = payload.get("sub")

    # Находим пользователя в БД (исключая удалённые)
    try:
        user = User.objects.get(id=user_id, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("user not found")

    # Получаем текущее время для проверки срока действия токенов в БД
    now = timezone.now()

    # Флаг: найден ли валидный токен в БД
    valid_token_exists = False

    # Перебираем все access-токены пользователя, которые ещё не отозваны и не истекли
    for token_record in UserToken.objects.filter(
        user=user,
        token_type="access",
        revoked=False,
        expires_at__gt=now,
    ):
        # Вычисляем хеш предъявленного токена с той же солью, что хранится в БД
        calculated_hash = hash_token(access_token, token_record.token_salt)
        # Сравниваем с сохранённым хешем
        if calculated_hash == token_record.token_hash:
            valid_token_exists = True
            break

    # Если токен не найден в БД (отозван или не существует) — доступ запрещён
    if not valid_token_exists:
        raise ValueError("token revoked or not found")

    return user


def refresh_user_tokens(refresh_token: str):
    """
    Обновление пары токенов по refresh-токену.
    Проверяет валидность refresh-токена, отзывает старый,
    генерирует новую пару (access + refresh) и сохраняет в БД.
    """
    # Декодируем refresh-токен и проверяем подпись
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise ValueError("invalid or expired refresh token")

    # Убеждаемся, что токен именно refresh-типа
    if payload.get("type") != "refresh":
        raise ValueError("invalid token type")

    # Извлекаем ID пользователя из токена
    user_id = payload.get("sub")

    # Находим пользователя в БД
    try:
        user = User.objects.get(id=user_id, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("user not found")

    # Текущее время для проверки срока действия
    now = timezone.now()

    # Переменная для хранения найденной записи refresh-токена
    current_token_record = None

    # Ищем активный (не отозванный, не истёкший) refresh-токен пользователя
    for token_record in UserToken.objects.filter(
        user=user,
        token_type="refresh",
        revoked=False,
        expires_at__gt=now,
    ):
        # Сверяем хеш предъявленного токена с записью в БД
        calculated_hash = hash_token(refresh_token, token_record.token_salt)
        if calculated_hash == token_record.token_hash:
            current_token_record = token_record
            break

    # Если токен не найден (отозван или истёк) — ошибка
    if current_token_record is None:
        raise ValueError("refresh token revoked or not found")

    # Отзываем старый refresh-токен (помечаем как отозванный)
    current_token_record.revoked = True
    current_token_record.save()

    # Генерируем новую пару токенов
    access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    # Генерируем новые соли для токенов
    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    # Вычисляем время истечения
    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    # Сохраняем новый access-токен (в хешированном виде) в БД
    UserToken.objects.create(
        user=user,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

    # Сохраняем новый refresh-токен (в хешированном виде) в БД
    UserToken.objects.create(
        user=user,
        token_hash=hash_token(new_refresh_token, refresh_salt),
        token_salt=refresh_salt,
        token_type="refresh",
        expires_at=refresh_expiration,
        revoked=False,
    )

    return user, access_token, new_refresh_token


def logout_user(access_token: str):
    """
    Завершение текущей сессии.
    Находит access-токен в БД и помечает его как отозванный.
    """
    # Текущее время для фильтрации активных токенов
    now = timezone.now()

    # Ищем все активные access-токены (не отозванные, не истёкшие)
    for token_record in UserToken.objects.filter(
        token_type="access",
        revoked=False,
        expires_at__gt=now,
    ):
        # Вычисляем хеш предъявленного токена с солью из записи
        calculated_hash = hash_token(access_token, token_record.token_salt)

        # Если нашли совпадение — отзываем токен
        if calculated_hash == token_record.token_hash:
            token_record.revoked = True
            token_record.save()
            break


def logout_all_user_sessions(access_token: str):
    """
    Завершение ВСЕХ сессий пользователя.
    Извлекает пользователя из токена и отзывает все его токены (access + refresh).
    """
    # Получаем объект пользователя из access-токена (с валидацией)
    user = get_current_user_from_access_token(access_token)

    # Массово помечаем все токены пользователя как отозванные
    UserToken.objects.filter(
        user=user,
        revoked=False,
    ).update(revoked=True)

    return user