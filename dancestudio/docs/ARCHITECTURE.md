# Архитектура

## Общая схема
1. Пользователь взаимодействует с Telegram-ботом (aiogram), который общается с backend через REST API и Redis для блокировок.
2. Backend (FastAPI) управляет бизнес-логикой: бронирования, оплаты, управление расписанием.
3. Admin-frontend (React) использует API для CRUD и аналитики.
4. PostgreSQL хранит данные, Alembic обеспечивает миграции.
5. Redis используется для rate-limit и блокировок при бронировании/очередях.
6. APScheduler в `backend/workers/scheduler.py` отправляет напоминания и обрабатывает waitlist.
7. PaymentGateway абстрагирует интеграцию оплаты, текущая реализация — YooKassa.

## Поток бронирования
- Бот вызывает `book_class` через API.
- `booking_service.book_class` берёт row-level lock на слот, проверяет capacity и наличие абонементов.
- При наличии подходящего абонемента списывает посещение и подтверждает бронь.
- Иначе создаётся бронирование в статусе `reserved` и инициируется платёж через `payment_service`.
- Webhook оплаты обрабатывается эндпоинтом `/payments/webhook`, который обновляет `Payment` и `Booking` атомарно, логируя событие в `AuditLog`.

## Отмена и waitlist
- `booking_service.cancel_booking` проверяет правило 24 часов.
- При валидной отмене возвращаются посещения или создаётся кредит.
- Если освобождается место, `schedule_service` уведомляет пользователей из waitlist через бота.

## Google Sheets
- Модуль `google_sheets.py` содержит заглушку для экспорта. Он активируется только если `GOOGLE_SHEETS_ENABLED=true`.
