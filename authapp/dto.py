# re — модуль для работы с регулярными выражениями (валидация пароля)
import re


class RegisterDTO:
    """
    Data Transfer Object для регистрации пользователя.
    Принимает сырые данные из запроса, валидирует их
    и предоставляет безопасный интерфейс для сервисного слоя.
    
    Валидация пароля:
    - Минимум 6 символов
    - Без кириллицы
    - Только латиница, цифры и спецсимволы
    """

    def __init__(self, data: dict):
        """
        Инициализация DTO из словаря (распарсенный JSON запроса).
        Извлекает поля email, password, phone и запускает валидацию.
        """
        # Извлекаем данные из словаря (могут быть None)
        self.email = data.get("email")
        self.password = data.get("password")
        self.phone = data.get("phone")

        # Запускаем валидацию — если не пройдёт, будет выброшено исключение
        self.validate()

    def validate(self):
        """
        Комплексная валидация всех полей.
        Выбрасывает ValueError с описанием проблемы.
        """
        # Email обязателен
        if not self.email:
            raise ValueError("email is required")

        # Пароль обязателен
        if not self.password:
            raise ValueError("password is required")

        # Минимальная длина пароля
        if len(self.password) < 6:
            raise ValueError("password too short")
        
        # Проверка на кириллицу (запрещено)
        if self._has_cyrillic(self.password):
            raise ValueError("Пароль не должен содержать русские буквы")
        
        # Проверка формата: только разрешённые символы
        if not self._is_valid_password_format(self.password):
            raise ValueError("Пароль должен содержать только латинские буквы, цифры и спецсимволы (_-@#$%^&*!?)")

    def _has_cyrillic(self, text: str) -> bool:
        """
        Проверка наличия кириллических символов.
        Диапазон Unicode: \u0400-\u04FF (кириллица).
        Возвращает True, если найдены кириллические символы.
        """
        cyrillic_pattern = re.compile(r'[\u0400-\u04FF]')
        return bool(cyrillic_pattern.search(text))

    def _is_valid_password_format(self, password: str) -> bool:
        """
        Проверка, что пароль содержит только разрешённые символы.
        Разрешены: латиница (a-zA-Z), цифры (0-9), спецсимволы.
        Возвращает True, если формат корректен.
        """
        # Регулярное выражение: все символы из разрешённого набора
        allowed_pattern = re.compile(r'^[a-zA-Z0-9_\-\@#$%\^&\*\!\?\.\,\/\\\|\(\)\[\]\{\}\:\;\"\'`\~\+=\s]+$')
        return bool(allowed_pattern.match(password))


class LoginDTO:
    """
    Data Transfer Object для входа пользователя.
    Принимает email и пароль, валидирует их.
    """

    def __init__(self, data: dict):
        """
        Инициализация DTO из словаря.
        Извлекает email и password, запускает валидацию.
        """
        self.email = data.get("email")
        self.password = data.get("password")

        self.validate()

    def validate(self):
        """
        Валидация полей для входа.
        Email и пароль обязательны, пароль проверяется на формат.
        """
        # Email обязателен
        if not self.email:
            raise ValueError("email is required")

        # Пароль обязателен
        if not self.password:
            raise ValueError("password is required")
        
        # Проверка на кириллицу
        if self._has_cyrillic(self.password):
            raise ValueError("Пароль не должен содержать русские буквы")
        
        # Проверка формата пароля
        if not self._is_valid_password_format(self.password):
            raise ValueError("Пароль должен содержать только латинские буквы, цифры и спецсимволы (_-@#$%^&*!?)")

    def _has_cyrillic(self, text: str) -> bool:
        """Проверка на кириллицу (аналогично RegisterDTO)."""
        cyrillic_pattern = re.compile(r'[\u0400-\u04FF]')
        return bool(cyrillic_pattern.search(text))

    def _is_valid_password_format(self, password: str) -> bool:
        """Проверка формата пароля (аналогично RegisterDTO)."""
        allowed_pattern = re.compile(r'^[a-zA-Z0-9_\-\@#$%\^&\*\!\?\.\,\/\\\|\(\)\[\]\{\}\:\;\"\'`\~\+=\s]+$')
        return bool(allowed_pattern.match(password))