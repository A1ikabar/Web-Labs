# bcrypt — библиотека для хеширования паролей с солью
# secrets — генерация криптографически стойких случайных значений
# hashlib — хеширование токенов (SHA256)
import bcrypt
import secrets
import hashlib


def hash_password(password: str) -> tuple[str, str]:
    """
    Хеширование пароля с использованием bcrypt.
    Автоматически генерирует уникальную соль для каждого вызова.
    Возвращает кортеж: (хеш пароля, соль).
    
    Почему bcrypt:
    - Адаптивная функция хеширования (можно увеличивать сложность)
    - Устойчива к brute-force атакам
    - Соль хранится вместе с хешем в формате $algorithm$cost$salt$hash
    """
    # Генерируем случайную соль (bcrypt.gensalt создаёт соль с cost-фактором)
    salt = bcrypt.gensalt()
    # Хешируем пароль с солью
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    # Возвращаем хеш и соль (соль нужна для последующей верификации)
    return password_hash, salt.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Проверка пароля путём сравнения с хешем из БД.
    Извлекает соль из хеша и проверяет совпадение.
    Возвращает True, если пароль верный.
    """
    # bcrypt.checkpw автоматически извлекает соль из password_hash
    # и сверяет хеш введённого пароля с сохранённым
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_token_salt() -> str:
    """
    Генерация криптографически стойкой соли для токенов.
    Возвращает 32-символьную hex-строку (16 байт случайных данных).
    Используется для безопасного хранения токенов в БД.
    """
    # secrets.token_hex(16) генерирует 16 случайных байт → 32 hex-символа
    return secrets.token_hex(16)


def hash_token(token: str, salt: str) -> str:
    """
    Одностороннее хеширование токена с солью (SHA256).
    Токен конкатенируется с солью, затем хешируется.
    Результат — 64-символьная hex-строка (256 бит).
    
    Зачем:
    - Токены не хранятся в БД в открытом виде
    - При утечке БД злоумышленник не получит сами токены
    - Соль предотвращает rainbow table атаки
    """
    # Конкатенируем токен с солью и хешируем через SHA256
    return hashlib.sha256(f'{token}{salt}'.encode('utf-8')).hexdigest()