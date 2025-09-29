# API Reference

Базовый URL: `/api/v1`

## Аутентификация
### POST /auth/login
Вход администратора. Возвращает JWT.

```json
{
  "email": "admin@example.com",
  "password": "string"
}
```

Ответ:
```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

### GET /auth/me
Возвращает информацию о текущем администраторе.

## Directions
- `GET /directions` — список направлений.
- `POST /directions` — создание направления.
- `PATCH /directions/{id}` — обновление.
- `DELETE /directions/{id}` — удаление.

## Slots
- `GET /slots?from=&to=&direction_id=` — фильтр по датам и направлению.
- `POST /slots` — батч-создание расписания.
- `PATCH /slots/{id}` — обновление параметров.
- `DELETE /slots/{id}` — удаление.
- `POST /slots/{id}/cancel` — отмена слота.

## Products
CRUD аналогично направлениям. Тип `subscription` поддерживает `classes_count` и `validity_days`.

## Bookings
- `GET /bookings` — фильтры по слоту/пользователю.
- `POST /bookings` — администратор создаёт бронирование.
- `POST /bookings/{id}/cancel` — отмена админом.
- `GET /bookings/stats` — агрегированная статистика.

## Payments
- `GET /payments` — список платежей.
- `POST /payments/create` — инициировать оплату разового визита.
- `POST /payments/webhook` — колбек провайдера (без аутентификации).

## Users
- `GET /users` — список.
- `GET /users/{id}` — детальная информация.
- `PATCH /users/{id}` — обновление профиля.

## Служебное
- `POST /export/google-sheets` — экспорт (заглушка, логирует при включённом флаге).
- `GET /health` — проверка состояния сервиса.
