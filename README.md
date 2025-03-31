# Проект: Сервис сокращения ссылок

## Описание API

Сервис предоставляет API для создания, управления и получения сокращенных ссылок.

## Методы API

### Регистрация

**POST** `/register` – Регистрация нового пользователя.

#### Пример запроса:

```json
{
  "username": "test",
  "email": "test@example.com",
  "password": "test"
}
```

#### Результат запроса:

```json
{
  "username": "test",
  "email": "test@example.com",
  "id": 15,
  "is_active": true
}
```

### Аутентификация

**POST** `/login` – Вход в систему.

#### Пример запроса:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&username=test&password=test&scope=&client_id=string&client_secret=string'
```

#### Результат запроса:

```json
{
  "token": "YOUR TOKEN"
}
```

### Создание короткой ссылки

**POST** `/links/shorten` – Создает сокращенную ссылку.

#### Пример запроса:

```json
{
  "original_url": "https://www.google.ru/?hl=ru",
  "custom_alias": "abcdefg",
  "expires_at": "2025-03-31T17:00:00.158Z",
  "owner_id": 0
}
```

#### Результат запроса:

```json
{
  "id": 17,
  "original_url": "https://www.google.ru/?hl=ru",
  "short_code": "abcdefg",
  "created_at": "2025-03-31T16:19:27.182210",
  "expires_at": "2025-04-01T16:19:27.180220",
  "is_permanent": false,
  "last_accessed": "2025-03-31T16:19:27.182210",
  "clicks": 0
}
```

### Перенаправление по короткой ссылке

**GET** `/links/{short_code}` – Перенаправляет на оригинальную ссылку.

#### Пример запроса:

```
curl -X 'GET' \
  'http://127.0.0.1:8000/links/abcdefg' \
  -H 'accept: application/json'
```

#### Результат запроса:

```
Redirect
```

### Удаление короткой ссылки

**DELETE** `/links/{short_code}` – Удаляет указанную ссылку.

#### Пример запроса:

```
curl -X 'DELETE' \
  'http://127.0.0.1:8000/links/abcdefg?token=YOURTOKEN' \
  -H 'accept: application/json
```

#### Результат запроса:

```json
{
  "message": "Ссылка удалена"
}
```

### Обновление короткой ссылки

**PUT** `/links/{short_code}` – Обновляет короткое название для длинной ссылки

#### Пример запроса:

```
curl -X 'PUT' \
  'http://127.0.0.1:8000/links/abcdefNEW?original_url=https%3A%2F%2Fwww.google.ru%2F%3Fhl%3Dru&token=YOURTOKEN' \
  -H 'accept: application/json'
```

#### Результат запроса:

```json
{
  "original_url": "https://www.google.ru/?hl=ru",
  "short_code": "abcdefNEW",
  "expires_at": "2025-04-01T16:32:31.801853",
  "last_accessed": "2025-03-31T16:32:37.709281",
  "clicks": 2,
  "created_at": "2025-03-31T16:32:31.803319",
  "id": 18,
  "is_permanent": false,
  "owner_id": null
}
```

### Получение статистики по ссылке

**GET** `/links/{short_code}/stats` – Получает статистику переходов по ссылке.

#### Пример запроса:

```
curl -X 'PUT' \
  'http://127.0.0.1:8000/links/abcdefNEW?original_url=https%3A%2F%2Fwww.google.ru%2F%3Fhl%3Dru&token=YOURTOKEN' \
  -H 'accept: application/json'
```

#### Результат запроса:

```json
{
  "id": 18,
  "original_url": "https://www.google.ru/?hl=ru",
  "short_code": "abcdefNEW",
  "created_at": "2025-03-31T16:32:31.803319",
  "expires_at": "2025-04-01T16:32:31.801853",
  "is_permanent": false,
  "last_accessed": "2025-03-31T16:32:37.709281",
  "clicks": 2
}
```

### Получение оригинального URL

**GET** `/links/{short_code}/original` – Возвращает оригинальную ссылку.

#### Пример запроса:

```
curl -X 'GET' \
  'http://127.0.0.1:8000/links/abcdefNEW/original' \
  -H 'accept: application/json'
```

#### Результат запроса:

```json
{
  "original_url": "https://www.google.ru/?hl=ru"
}
```

### Обновление времени жизни ссылки

**POST** `/links/{short_code}/update_expiry` – Обновляет срок действия ссылки.

#### Пример запроса:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/links/abcdefNEW/update_expiry?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzQzNDM5Mzg0fQ.nw3FzFrc5m9lDCJEo58ftmrxN5tLcbENKx8lF4wLZYA' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "expires_at": "2025-03-31T16:40:25.696+00:00"
}'
```

#### Результат запроса:

```json
{
  "message": "Дата истечения ссылки обновлена",
  "expires_at": "2025-03-31T16:40:25.696000"
}
```


## Описание базы данных

База данных содержит таблицы:

- `users` – пользователи сервиса.
- `links` – сокращенные ссылки с оригинальными URL, сроком действия и статистикой переходов.

## Переменные окружения

Переменные хранятся в файле `.env` и используются для конфигурации приложения. Пример `.env`:

```
DB_USER=postgres
DB_PASS=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=postgres
SECRET_KEY=test1
ALGORITHM=HS256
REDIS_HOST='redis'
```

## Запуск через Docker Compose
0. Клонируйте репозиторий.
1. Создайте файл `.env` с нужными переменными окружения.
2. Запустите контейнеры:
   ```sh
   docker-compose up -d --build
   ```
3. API будет доступно по адресу: `http://localhost:8000/docs`.

## Остановка и перезапуск

- Остановка контейнеров:
  ```sh
  docker-compose down
  ```
- Перезапуск контейнеров:
  ```sh
  docker-compose restart
  ```

