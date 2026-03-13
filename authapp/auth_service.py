from authapp import dto
from users.models import User
from authapp.utils import hash_password
from authapp.utils import verify_password, generate_token_salt, hash_token
from authapp.jwt_utils import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from users.models import UserToken
from django.utils import timezone
from datetime import timedelta

def register_user(dto):
    existing_user = User.objects.filter(email=dto.email).first()
    if existing_user:
        raise ValueError("user with this email already exists")

    password_hash, password_salt = hash_password(dto.password)

    user = User.objects.create(
        email=dto.email,
        password_hash=password_hash,
        password_salt=password_salt,
    )

    return user

def login_user(email: str, password: str):
    try:
        user = User.objects.get(email=email, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("invalid email or password")

    if not verify_password(password, user.password_hash):
        raise ValueError("invalid email or password")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    UserToken.objects.create(
        user=user,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

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
    try:
        payload = decode_access_token(access_token)
    except Exception:
        raise ValueError("invalid or expired access token")

    if payload.get("type") != "access":
        raise ValueError("invalid token type")

    user_id = payload.get("sub")

    try:
        user = User.objects.get(id=user_id, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("user not found")

    now = timezone.now()

    valid_token_exists = False

    for token_record in UserToken.objects.filter(
        user=user,
        token_type="access",
        revoked=False,
        expires_at__gt=now,
    ):
        calculated_hash = hash_token(access_token, token_record.token_salt)
        if calculated_hash == token_record.token_hash:
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

    try:
        user = User.objects.get(id=user_id, deleted_at__isnull=True)
    except User.DoesNotExist:
        raise ValueError("user not found")

    now = timezone.now()

    current_token_record = None

    for token_record in UserToken.objects.filter(
        user=user,
        token_type="refresh",
        revoked=False,
        expires_at__gt=now,
    ):
        calculated_hash = hash_token(refresh_token, token_record.token_salt)
        if calculated_hash == token_record.token_hash:
            current_token_record = token_record
            break

    if current_token_record is None:
        raise ValueError("refresh token revoked or not found")

    current_token_record.revoked = True
    current_token_record.save()

    access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    access_salt = generate_token_salt()
    refresh_salt = generate_token_salt()

    access_expiration = timezone.now() + timedelta(minutes=15)
    refresh_expiration = timezone.now() + timedelta(days=7)

    UserToken.objects.create(
        user=user,
        token_hash=hash_token(access_token, access_salt),
        token_salt=access_salt,
        token_type="access",
        expires_at=access_expiration,
        revoked=False,
    )

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

        now = timezone.now()

        for token_record in UserToken.objects.filter(
            token_type="access",
            revoked=False,
            expires_at__gt=now,
        ):
            calculated_hash = hash_token(access_token, token_record.token_salt)

            if calculated_hash == token_record.token_hash:
                token_record.revoked = True
                token_record.save()
                break    

def logout_all_user_sessions(access_token: str):
    user = get_current_user_from_access_token(access_token)

    UserToken.objects.filter(
        user=user,
        revoked=False,
    ).update(revoked=True)

    return user