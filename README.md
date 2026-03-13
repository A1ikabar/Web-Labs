# Лабораторная работа №3

**Авторизация и аутентификация (JWT, Refresh Tokens, HttpOnly Cookies)**

## Краткое описание проекта

Данный проект представляет собой Django-приложение, разработанное как
продолжение лабораторной работы №2.\
Во второй лабораторной работе был реализован CRUD для сущности `Work` с
использованием PostgreSQL, Docker, UUID и Soft Delete.\
В рамках лабораторной работы №3 в существующее приложение была добавлена
система аутентификации и авторизации.

В проекте реализованы:

-   регистрация пользователя;
-   вход пользователя по email и паролю;
-   безопасное хеширование паролей;
-   генерация JWT Access Token и Refresh Token;
-   хранение токенов в базе данных в хешированном виде;
-   передача токенов через HttpOnly Cookies;
-   endpoint `/auth/whoami` для определения текущего авторизованного
    пользователя;
-   endpoint `/auth/refresh` для обновления пары токенов;
-   endpoint `/auth/logout` для завершения текущей сессии;
-   endpoint `/auth/logout-all` для завершения всех сессий пользователя;
-   защита ресурсов из лабораторной работы №2;
-   проверка владельца ресурса при изменении и удалении.

## Используемые технологии

-   Python
-   Django
-   PostgreSQL
-   Docker / Docker Compose
-   PyJWT
-   bcrypt
-   python-dotenv
-   Postman

## Структура проекта

-   `Settings/` --- настройки Django-проекта;
-   `lab2/` --- приложение с основной сущностью `Work`;
-   `users/` --- модели пользователей и токенов;
-   `authapp/` --- логика регистрации, входа, refresh, logout и whoami;
-   `.env` --- переменные окружения;
-   `docker-compose.yml` --- запуск PostgreSQL в Docker.

## Пример файла `.env.example`

``` env
SECRET_KEY=your_django_secret_key
DEBUG=True

DB_NAME=wp_labs
DB_USER=student
DB_PASSWORD=student_secure_password
DB_HOST=localhost
DB_PORT=5433

JWT_ACCESS_SECRET=your_access_secret
JWT_REFRESH_SECRET=your_refresh_secret
JWT_ACCESS_EXPIRATION_MINUTES=15
JWT_REFRESH_EXPIRATION_DAYS=7
```
