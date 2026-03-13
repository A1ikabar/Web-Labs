import re

class RegisterDTO:

    def __init__(self, data: dict):
        self.email = data.get("email")
        self.password = data.get("password")
        self.phone = data.get("phone")

        self.validate()

    def validate(self):

        if not self.email:
            raise ValueError("email is required")

        if not self.password:
            raise ValueError("password is required")

        if len(self.password) < 6:
            raise ValueError("password too short")
        if self._has_cyrillic(self.password):
            raise ValueError("Пароль не должен содержать русские буквы")
        if not self._is_valid_password_format(self.password):
            raise ValueError("Пароль должен содержать только латинские буквы, цифры и спецсимволы (_-@#$%^&*!?)")
        
    def _has_cyrillic(self, text: str) -> bool:
        cyrillic_pattern = re.compile(r'[\u0400-\u04FF]')
        return bool(cyrillic_pattern.search(text))
    
    def _is_valid_password_format(self, password: str) -> bool:
        allowed_pattern = re.compile(r'^[a-zA-Z0-9_\-\@#$%\^&\*\!\?\.\,\/\\\|\(\)\[\]\{\}\:\;\"\'`\~\+=\s]+$')
        return bool(allowed_pattern.match(password))

class LoginDTO:

    def __init__(self, data: dict):
        self.email = data.get("email")
        self.password = data.get("password")

        self.validate()

    def validate(self):

        if not self.email:
            raise ValueError("email is required")

        if not self.password:
            raise ValueError("password is required")
        if self._has_cyrillic(self.password):
            raise ValueError("Пароль не должен содержать русские буквы")
        if not self._is_valid_password_format(self.password):
            raise ValueError("Пароль должен содержать только латинские буквы, цифры и спецсимволы (_-@#$%^&*!?)")
        
    def _has_cyrillic(self, text: str) -> bool:
        cyrillic_pattern = re.compile(r'[\u0400-\u04FF]')
        return bool(cyrillic_pattern.search(text))
    
    def _is_valid_password_format(self, password: str) -> bool:
        allowed_pattern = re.compile(r'^[a-zA-Z0-9_\-\@#$%\^&\*\!\?\.\,\/\\\|\(\)\[\]\{\}\:\;\"\'`\~\+=\s]+$')
        return bool(allowed_pattern.match(password))