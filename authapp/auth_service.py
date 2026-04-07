from datetime import timedelta
from django.utils import timezone

from authapp.utils import hash_password, verify_password, generate_token_salt, hash_token
from authapp.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from common.cache_service import cache_service
from users.mongo_service import (
    create_user,
    find_user_by_email,
    find_user_by_id,
)
from users.token_mongo_service import (
    create_user_token,
    find_active_tokens_by_user_and_type,
    revoke_token_by_id,
    revoke_all_user_tokens,
)

def register_user(dto):
    existing_user = find_user_by_email(dto.email)
    if existing_user:
        raise ValueError("user with this email already exists")

    password_hash, password_salt = hash_password(dto.password)

    user = create_user(
        email=dto.email,
        phone=getattr(dto, "phone", None),
        password_hash=password_hash,
        password_salt=password_salt,
    )

    return user

def login_user(email: str, password: str):
    user = find_user_by_email(email)

    if not user:
        raise ValueError("invalid email or password")

    if not verify_password(password, user["password_hash"]):
        raise ValueError("invalid email or password")

    user_id = str(user["_id"])

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    access_payload = decode_access_token(access_token)
    access_jti = access_payload.get("jti")

    if access_jti:
        cache_key = f"wp:auth:user:{user_id}:access:{access_jti}"
        cache_service.set(cache_key, "valid", ttl=15 * 60)

    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    create_user_token(
        user_id=user_id,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

    create_user_token(
        user_id=user_id,
        token_hash=hash_token(refresh_token, refresh_salt),
        token_salt=refresh_salt,
        token_type="refresh",
        expires_at=refresh_expiration,
        revoked=False,
    )

    return user, access_token, refresh_token

def get_current_user_from_access_token(access_token: str):
    try:
        payload = decode_access_token(access_token)
    except Exception:
        raise ValueError("invalid or expired access token")

    if payload.get("type") != "access":
        raise ValueError("invalid token type")

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not jti:
        raise ValueError("invalid token: missing jti")

    cache_key = f"wp:auth:user:{user_id}:access:{jti}"
    cached_data = cache_service.get(cache_key)

    if cached_data is None:
        raise ValueError("token revoked or expired")

    user = find_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    now = timezone.now()
    token_records = find_active_tokens_by_user_and_type(user_id, "access", now)

    valid_token_exists = False
    for token_record in token_records:
        calculated_hash = hash_token(access_token, token_record["token_salt"])
        if calculated_hash == token_record["token_hash"]:
            valid_token_exists = True
            break

    if not valid_token_exists:
        raise ValueError("token revoked or not found")

    return user

def refresh_user_tokens(refresh_token: str):
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise ValueError("invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("invalid token type")

    user_id = payload.get("sub")

    user = find_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    now = timezone.now()
    token_records = find_active_tokens_by_user_and_type(user_id, "refresh", now)
    current_token_record = None
    for token_record in token_records:
        calculated_hash = hash_token(refresh_token, token_record["token_salt"])
        if calculated_hash == token_record["token_hash"]:
            current_token_record = token_record
            break

    if current_token_record is None:
        raise ValueError("refresh token revoked or not found")

    revoke_token_by_id(str(current_token_record["_id"]))

    access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    access_payload = decode_access_token(access_token)
    access_jti = access_payload.get("jti")

    if access_jti:
        cache_key = f"wp:auth:user:{user_id}:access:{access_jti}"
        cache_service.set(cache_key, "valid", ttl=15 * 60)

    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    create_user_token(
        user_id=user_id,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

    create_user_token(
        user_id=user_id,
        token_hash=hash_token(new_refresh_token, refresh_salt),
        token_salt=refresh_salt,
        token_type="refresh",
        expires_at=refresh_expiration,
        revoked=False,
    )

    return user, access_token, new_refresh_token

def logout_user(access_token: str):
    try:
        payload = decode_access_token(access_token)
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if user_id and jti:
            cache_service.delete(f"wp:auth:user:{user_id}:access:{jti}")
            cache_service.delete(f"wp:users:profile:{user_id}")
    except Exception:
        pass

    try:
        payload = decode_access_token(access_token)
        user_id = payload.get("sub")
    except Exception:
        return

    now = timezone.now()
    token_records = find_active_tokens_by_user_and_type(user_id, "access", now)

    for token_record in token_records:
        calculated_hash = hash_token(access_token, token_record["token_salt"])
        if calculated_hash == token_record["token_hash"]:
            revoke_token_by_id(str(token_record["_id"]))
            break

def logout_all_user_sessions(access_token: str):
    user = get_current_user_from_access_token(access_token)
    user_id = str(user["_id"])

    cache_service.delete_by_pattern(f"wp:auth:user:{user_id}:access:*")
    cache_service.delete(f"wp:users:profile:{user_id}")

    revoke_all_user_tokens(user_id)

    return user