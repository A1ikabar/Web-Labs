# Web-Labs

Проект выполнен в рамках лабораторных работ по веб-программированию.  
В проекте реализовано Django API с использованием MongoDB, Redis, RabbitMQ, MinIO, Docker и Kubernetes.

## Лабораторная работа №9 — Kubernetes, health checks и масштабирование

### Цель работы

Цель лабораторной работы — познакомиться с горизонтальным масштабированием веб-приложений на примере Kubernetes, изучить liveness/readiness probes и реализовать защиту от повторной обработки событий с помощью Redis-блокировки.

---

## Что реализовано

В рамках лабораторной работы №9 было добавлено:

- Dockerfile для сборки API-образа.
- Отдельный `requirements-docker.txt` для сборки Linux Docker-образа.
- Kubernetes-манифесты для запуска проекта.
- Health endpoints:
  - `GET /health`
  - `GET /health/live`
  - `GET /health/ready`
- Readiness-проверка зависимостей:
  - MongoDB
  - Redis
  - RabbitMQ
  - MinIO
- Liveness-проверка приложения.
- Deployment и Service для API.
- Deployment для consumer-а события регистрации пользователя.
- Kubernetes-манифесты для MongoDB, Redis, MinIO и RabbitMQ.
- Горизонтальное масштабирование API до 4 pod-ов.
- Redis-lock для защиты от повторной обработки события регистрации пользователя.

---

## Используемые сервисы

Проект использует следующие сервисы:

| Сервис | Назначение |
|---|---|
| Django | Backend API |
| MongoDB | Основная база данных |
| Redis | Кэш, хранение токенов, distributed lock |
| RabbitMQ | Очередь событий |
| MinIO | Объектное хранилище файлов |
| Kubernetes | Оркестрация контейнеров |
| Docker | Контейнеризация приложения |

---

## Health endpoints

### `GET /health`

Общий health endpoint приложения.

Пример ответа:

```json
{
  "status": "ok",
  "service": "wp-labs-api"
}
```

### `GET /health/live`

Liveness endpoint.  
Проверяет, что процесс приложения запущен и отвечает.

Пример ответа:

```json
{
  "status": "alive"
}
```

### `GET /health/ready`

Readiness endpoint.  
Проверяет готовность приложения принимать трафик и доступность внешних зависимостей:

- MongoDB
- Redis
- RabbitMQ
- MinIO

Пример успешного ответа:

```json
{
  "status": "ready",
  "dependencies": {
    "mongo": {
      "ok": true
    },
    "redis": {
      "ok": true
    },
    "rabbitmq": {
      "ok": true
    },
    "minio": {
      "ok": true
    }
  }
}
```

Если хотя бы одна зависимость недоступна, endpoint возвращает статус `503`.

---

## Подготовка к запуску

Перед запуском необходимо убедиться, что установлены:

- Docker Desktop
- Docker Compose
- Kubernetes в Docker Desktop
- kubectl
- curl или Postman/Insomnia

В Docker Desktop должен быть включён Kubernetes:

```text
Docker Desktop → Settings → Kubernetes → Enable Kubernetes
```

После запуска Docker Desktop необходимо дождаться статусов:

```text
Engine running
Kubernetes running
```

---

## Сборка Docker-образа

В корне проекта выполнить:

```bash
docker build -t wp-labs/api:1.0.0 .
```

Для Docker используется файл:

```text
requirements-docker.txt
```

Он нужен для корректной сборки Linux Docker-образа.

---

## Запуск приложения в Kubernetes

Сначала применить namespace:

```bash
kubectl apply -f k8s/00-namespace.yaml
```

Затем применить Secret:

```bash
kubectl apply -f k8s/01-secrets.yaml
```

Далее применить манифесты сервисов:

```bash
kubectl apply -f k8s/02-mongodb/
kubectl apply -f k8s/03-redis/
kubectl apply -f k8s/04-minio/
kubectl apply -f k8s/05-rabbitmq/
kubectl apply -f k8s/06-api/
```

---

## Проверка состояния Kubernetes

Проверить node:

```bash
kubectl get nodes
```

Ожидаемый результат:

```text
docker-desktop   Ready
```

Проверить pod-ы проекта:

```bash
kubectl get pods -n wp-labs
```

Ожидаемый результат: все pod-ы должны быть в статусе `Running`.

Пример:

```text
api-...                         1/1   Running
mongodb-...                     1/1   Running
redis-...                       1/1   Running
minio-...                       1/1   Running
rabbitmq-...                    1/1   Running
user-registered-consumer-...    1/1   Running
```

Проверить все ресурсы namespace:

```bash
kubectl get all -n wp-labs
```

---

## Проброс порта API

Для доступа к API через локальный компьютер выполнить:

```bash
kubectl port-forward svc/api 4200:4200 -n wp-labs
```

После этого API будет доступно по адресу:

```text
http://127.0.0.1:4200
```

Важно: терминал с `port-forward` должен оставаться открытым.

---

## Проверка health endpoints

Во втором терминале выполнить:

```bash
curl http://127.0.0.1:4200/health
curl http://127.0.0.1:4200/health/live
curl http://127.0.0.1:4200/health/ready
```

Для Windows PowerShell:

```powershell
curl.exe http://127.0.0.1:4200/health
curl.exe http://127.0.0.1:4200/health/live
curl.exe http://127.0.0.1:4200/health/ready
```

Ожидаемый результат для `/health/ready`:

```json
{
  "status": "ready"
}
```

---

## Масштабирование API

Для горизонтального масштабирования API до 4 реплик выполнить:

```bash
kubectl scale deployment/api --replicas=4 -n wp-labs
```

Проверить pod-ы API:

```bash
kubectl get pods -n wp-labs -l app=api
```

Ожидаемый результат: должно быть 4 pod-а API в статусе `Running`.

Пример:

```text
api-...   1/1   Running
api-...   1/1   Running
api-...   1/1   Running
api-...   1/1   Running
```

---

## Проверка регистрации пользователя

В проекте регистрация пользователя выполняется через endpoint:

```http
POST /auth/register
```

Для проверки можно создать файл `register.json`:

```json
{
  "email": "test-k8s@example.com",
  "password": "strongPassword123",
  "phone": "+79990000000"
}
```

Отправить запрос:

```bash
curl -X POST http://127.0.0.1:4200/auth/register \
  -H "Content-Type: application/json" \
  --data-binary "@register.json"
```

Для Windows PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:4200/auth/register" -H "Content-Type: application/json" --data-binary "@register.json"
```

При успешной регистрации API возвращает данные созданного пользователя.

Пример ответа:

```json
{
  "id": "user_id",
  "email": "test-k8s@example.com"
}
```

Если пользователь уже существует, необходимо изменить email в `register.json`.

---

## Проверка consumer-а

Consumer обрабатывает событие регистрации пользователя из RabbitMQ.

Посмотреть логи consumer-а:

```bash
kubectl logs -l app=user-registered-consumer -n wp-labs --tail=100
```

Consumer запускается отдельным Deployment:

```text
user-registered-consumer
```

---

## Redis-lock

При регистрации пользователя приложение публикует событие `user.registered` в RabbitMQ.  
Consumer получает это событие и отправляет приветственное письмо.

Для защиты от повторной обработки события при масштабировании consumer-а добавлена Redis-блокировка.

Используется логика:

1. Проверяется, было ли событие уже обработано.
2. Создаётся lock в Redis.
3. Если lock получен, consumer выполняет обработку события.
4. После обработки событие помечается как обработанное.
5. Lock удаляется атомарно через Redis Lua script.

Это предотвращает повторную обработку одного и того же события несколькими pod-ами.

---

## Масштабирование consumer-а

Для проверки distributed lock можно масштабировать consumer:

```bash
kubectl scale deployment/user-registered-consumer --replicas=4 -n wp-labs
```

Проверить pod-ы consumer-а:

```bash
kubectl get pods -n wp-labs -l app=user-registered-consumer
```

После этого можно зарегистрировать нового пользователя и проверить логи:

```bash
kubectl logs -l app=user-registered-consumer -n wp-labs --tail=200
```

---

## Повторный запуск после перезагрузки компьютера

После перезагрузки компьютера не нужно вручную запускать `python manage.py runserver`.

Приложение запускается внутри Kubernetes pod-а.

Необходимо:

1. Открыть Docker Desktop.
2. Дождаться статусов:
   - `Engine running`
   - `Kubernetes running`
3. Открыть VS Code с проектом.
4. Проверить Kubernetes:

```bash
kubectl get nodes
kubectl get pods -n wp-labs
```

Если pod-ы существуют и находятся в статусе `Running`, можно сразу выполнять:

```bash
kubectl port-forward svc/api 4200:4200 -n wp-labs
```

Если namespace отсутствует, необходимо повторно применить манифесты:

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-secrets.yaml
kubectl apply -f k8s/02-mongodb/
kubectl apply -f k8s/03-redis/
kubectl apply -f k8s/04-minio/
kubectl apply -f k8s/05-rabbitmq/
kubectl apply -f k8s/06-api/
```

---

## Возможные проблемы

### API pod в статусе `ImagePullBackOff`

Проверить наличие Docker-образа:

```bash
docker images
```

Если образа `wp-labs/api:1.0.0` нет, собрать его заново:

```bash
docker build -t wp-labs/api:1.0.0 .
```

Затем перезапустить Deployment:

```bash
kubectl rollout restart deployment/api -n wp-labs
kubectl rollout restart deployment/user-registered-consumer -n wp-labs
```

### Порт 4200 занят

Если порт `4200` занят, можно использовать другой локальный порт:

```bash
kubectl port-forward svc/api 4201:4200 -n wp-labs
```

Тогда приложение будет доступно по адресу:

```text
http://127.0.0.1:4201
```

### Docker Desktop завис

Если Docker Desktop завис после перезапуска, можно выполнить:

```powershell
wsl --shutdown
```

После этого снова открыть Docker Desktop.

---

## Очистка Kubernetes-ресурсов

Удалить весь namespace вместе со всеми ресурсами:

```bash
kubectl delete namespace wp-labs
```

---

## Основные команды для защиты лабораторной работы

Проверить Kubernetes:

```bash
kubectl get nodes
kubectl get pods -n wp-labs
kubectl get all -n wp-labs
```

Пробросить порт API:

```bash
kubectl port-forward svc/api 4200:4200 -n wp-labs
```

Проверить health endpoints:

```bash
curl http://127.0.0.1:4200/health
curl http://127.0.0.1:4200/health/live
curl http://127.0.0.1:4200/health/ready
```

Масштабировать API:

```bash
kubectl scale deployment/api --replicas=4 -n wp-labs
kubectl get pods -n wp-labs -l app=api
```

Проверить регистрацию пользователя:

```bash
curl -X POST http://127.0.0.1:4200/auth/register \
  -H "Content-Type: application/json" \
  --data-binary "@register.json"
```

Проверить consumer:

```bash
kubectl logs -l app=user-registered-consumer -n wp-labs --tail=100
```
