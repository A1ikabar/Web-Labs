import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

def validate_smtp_config():
    required = {
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_USER": settings.SMTP_USER,
        "SMTP_PASS": settings.SMTP_PASS,
        "SMTP_FROM": settings.SMTP_FROM,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise RuntimeError(f"Missing SMTP settings: {', '.join(missing)}")

def send_welcome_email(to_email: str, display_name: str, user_id: str):
    validate_smtp_config()

    subject = "Добро пожаловать!"

    text_body = f"""
Здравствуйте, {display_name}!

Ваша регистрация успешно завершена.

Ваш ID аккаунта: {user_id}

Войти в систему:
{settings.LOGIN_URL}
"""

    html_body = f"""
<html>
  <body>
    <h2>Здравствуйте, {display_name}!</h2>
    <p>Ваша регистрация успешно завершена.</p>
    <p><b>ID аккаунта:</b> {user_id}</p>
    <p>
      <a href="{settings.LOGIN_URL}">Войти в систему</a>
    </p>
  </body>
</html>
"""

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email

    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    if settings.SMTP_SECURE:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(message)