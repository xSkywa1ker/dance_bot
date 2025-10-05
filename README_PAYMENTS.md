# Telegram Payments Demo (YooKassa)

Этот пример показывает, как подключить оплату через Telegram Bot Payments API с провайдером YooKassa на aiogram v3.

## Требования

- Python 3.11+
- Установленные зависимости из `requirements.txt`

## Быстрый старт

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Скопируйте файл окружения и заполните значения:
   ```bash
   cp .env.example .env
   ```
   Отредактируйте `.env`, указав реальные токены и параметры товара.
3. В @BotFather включите Payments, выберите провайдера **YooKassa** и получите *Provider Token*. Вставьте его в `.env` (переменная `PROVIDER_TOKEN`).
4. Запустите демо-бота:
   ```bash
   python main_payments_demo.py
   ```

## Проверка

- `/start` → бот отправляет приветствие и кнопку «Купить».
- `/buy` → приходит invoice с кнопкой «Оплатить».
- Проведите тестовую оплату → бот отправит сообщение «Оплата прошла успешно…» с реквизитами платежа.

## Частые ошибки

- `PAYMENT_PROVIDER_INVALID` → проверьте, что используете Provider Token из @BotFather и выбран провайдер YooKassa.
- Нет `successful_payment` → убедитесь, что обработчик `pre_checkout_query` отвечает `ok=True`.
- Неверная сумма → укажите цену в копейках (`PRICE_RUB_CENTS`).

### Что означает «Не удалось отправить счёт через Telegram»?

Такой текст бот показывает, когда Telegram Bot API отклоняет вызов `sendInvoice`. Чаще всего
это происходит по одной из следующих причин:

- неверный `provider_token` или токен относится к другому боту (`PAYMENT_PROVIDER_INVALID`,
  `PAYMENT_PROVIDER_MISMATCH`);
- указана неподдерживаемая валюта или она не совпадает с настройкой бота (`CURRENCY_NOT_SUPPORTED`);
- сумма счёта не проходит валидацию Telegram (`CURRENCY_TOTAL_AMOUNT_INVALID`,
  `AMOUNT_NOT_ENOUGH`).

Чтобы увидеть конкретную подсказку, включите логирование предупреждений и проверьте вывод
бота — вместе с ошибкой придёт пояснение, которое можно показать пользователю.

## Встраивание в проект

Импортируйте `handlers.payments.router` в свой `Dispatcher` и добавьте обработчики, как показано в `main_payments_demo.py`.
