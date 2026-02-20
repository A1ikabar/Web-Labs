# Web-Labs
# New Year Countdown API

Простой Django сервис, который возвращает количество дней до Нового года.

## Требования

- Docker и Docker Compose (рекомендуемый способ)
- ИЛИ Python 3.11 и pip (для локального запуска)

## Запуск с использованием Docker

### Сборка и запуск контейнера

```bash
# Сборка образа и запуск контейнера
docker-compose up --build

# Или по отдельности:
docker build -t new-year-countdown .
docker run -p 4200:4200 new-year-countdown