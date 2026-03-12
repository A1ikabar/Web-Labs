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