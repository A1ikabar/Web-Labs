FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Открытие порта
EXPOSE 4200

# Команда для запуска приложения
CMD ["python", "manage.py", "runserver", "0.0.0.0:4200"]