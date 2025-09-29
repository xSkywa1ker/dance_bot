# DanceStudioBot

## Запуск

```bash
cp deploy/env/.env.example deploy/env/.env  # необязательно, make up создаст файл автоматически
make up           # поднять docker-compose
make migrate      # применить миграции
make seed         # загрузить тестовые данные
```

После запуска сервисы доступны по:
- Backend API: http://localhost:8000/api/v1/docs
- Админ-панель: http://localhost:5173/
- Telegram-бот: подключите токен из `.env`.

## Структура
- `bot/` — Telegram бот на aiogram
- `backend/` — FastAPI приложение с Alembic, SQLAlchemy, APScheduler
- `admin-frontend/` — React 18 + Vite админка
- `deploy/` — docker-compose, Nginx и примеры `.env`

## Доступы
При выполнении `make seed` создаётся администратор:
- email: `admin@example.com`
- пароль: `admin123`
