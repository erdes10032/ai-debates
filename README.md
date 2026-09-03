# AI Debates

Веб-платформа для организации дискуссий между несколькими LLM-агентами на заданную тему с формированием итогового консенсуса.

Пользователь создаёт дебаты, выбирает участников (модель + роль + позиция), после чего система проводит раунды аргументов в фоне и транслирует ход обсуждения в реальном времени.

---

## Технологии

- Python 3.12
- Django
- Django Channels (WebSocket)
- Celery
- Redis
- PostgreSQL
- OpenRouter API
- django-allauth
- Docker / Docker Compose
- Pytest

---

Компоненты системы:

- **Django (web)** — веб-интерфейс, авторизация, управление дебатами
- **Celery Worker** — фоновый запуск дебатов через `DebateEngine`
- **Redis** — брокер Celery и channel layer для WebSocket
- **PostgreSQL** — хранение пользователей, дебатов и сообщений
- **OpenRouter** — генерация ответов LLM-моделей
- **Django Admin** — управление моделями и ролями участников

---

## Архитектура

```
User (browser)
     │
 Django (HTTP)
     │
 Celery task ──► DebateEngine ──► OpenRouter API
     │                  │
     │                  ▼
     │            PostgreSQL
     │
 WebSocket ◄── Redis (Channels)
```

---

## Работа системы

1. Пользователь регистрируется и подтверждает email
2. Создаёт дебаты: тема, число раундов, участники (2–10)
3. Для каждого участника выбираются LLM-модель, роль и позиция (за / против)
4. Celery запускает задачу `run_debate_task`
5. `DebateEngine` проводит раунды: каждый участник генерирует аргумент через OpenRouter
6. Сообщения сохраняются в БД и отправляются клиенту по WebSocket
7. При включённых уступках участник может признать поражение
8. После завершения формируется текст консенсуса
9. Историю дебатов можно скачать в PDF

---

## Дополнительные возможности

### Роли и модели

В админ-панели настраиваются:

- **LLMModel** — доступные модели OpenRouter
- **DebateRole** — поведение участника (например, критик, эксперт)

### Уступки (concessions)

Если опция включена, участник может признать, что его позиция больше не защищаема. Дебаты могут завершиться досрочно.

### Профиль пользователя

- Аватар, био, пол
- Список созданных дебатов

### Локализация

Интерфейс поддерживает английский и русский языки.

---

## Основные URL

| URL | Описание |
|-----|----------|
| `/` | Главная страница |
| `/debates/` | Список дебатов пользователя |
| `/debates/create/` | Создание дебата |
| `/debates/<id>/` | Страница дебата (WebSocket) |
| `/debates/<id>/history/pdf/` | Скачивание PDF |
| `/users/profile/` | Профиль |
| `/accounts/` | Вход, регистрация, сброс пароля |
| `/admin/` | Админ-панель |

---

## Установка (Docker)

**1. Клонировать репозиторий**

```bash
git clone https://github.com/erdes10032/ai-debates.git
cd ai-debates
```

---

**2. Заполнить файл `.env`**

Заполните файл `.env` своими данными

Для Docker `DB_HOST`, `CELERY_BROKER_URL` и `REDIS_URL` переопределяются в `docker-compose.yml`.

---

**3. Запустить проект**

```bash
docker compose up --build
```

Будут запущены контейнеры:

```
web
celery
db
redis
```

При старте `web` автоматически выполняет миграции, собирает статику и запускает **Daphne** (ASGI + WebSocket).

---

**3. Создать суперпользователя**

```bash
docker compose exec web python manage.py createsuperuser
```

---

**4. Приложение будет доступно по адресу**

```
http://localhost:8000
```

Админ-панель:

```
http://localhost:8000/admin/
```

---

## База данных

### Debate

| Поле | Тип |
|------|-----|
| id | integer |
| user_id | FK → User |
| topic | string |
| status | pending / in_progress / completed / failed |
| rounds_count | integer |
| allow_concessions | boolean |
| consensus | text |
| created_at | datetime |

---

### DebateParticipant

| Поле | Тип |
|------|-----|
| id | integer |
| debate_id | FK → Debate |
| llm_model_id | FK → LLMModel |
| debate_role_id | FK → DebateRole |
| order | integer |
| position | support / oppose |
| has_conceded | boolean |

---

### DebateMessage

| Поле | Тип |
|------|-----|
| id | integer |
| debate_id | FK → Debate |
| round_id | FK → DebateRound |
| participant_id | FK → DebateParticipant |
| content | text |
| created_at | datetime |

---

## Тесты

Запуск через Docker:

```bash
docker compose exec web pytest
```

Тестируются:

- движок дебатов и уступки
- представления и формы
- валидация пользовательских данных
