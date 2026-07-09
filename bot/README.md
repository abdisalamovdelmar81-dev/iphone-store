# Telegram-бот магазина iPhone

Версия 2: роли админа и клиента, каталог, корзина, заказ с адресом, уведомление админу, поиск по имени и цвет товара.

## Как узнать ID админа

1. Создай бота у `@BotFather` и получи `BOT_TOKEN`.
2. Запусти бота.
3. Напиши боту `/id` или нажми `Мой ID`.
4. Скопируй число в `ADMIN_IDS`.

Можно указать несколько админов через запятую:

```env
ADMIN_IDS=123456789,987654321
```

## Команды

- `/start` - открыть меню.
- `/id` - узнать свой Telegram ID.
- `/catalog` - открыть каталог.
- `/cart` - открыть корзину.
- `/search` - поиск по названию или цвету.
- `/add` - добавить товар, только для админа.

Быстрое добавление товара:

```text
/add iPhone 16 Pro 256 ГБ | 5 | 119990 | Пустынный титан
```

Или нажми `Добавить товар` и бот спросит: имя, количество, цену, цвет.

## Локальный запуск

Создай файл `bot/.env` по примеру `bot/.env.example`:

```env
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=твой_telegram_id
DATA_DIR=./data
```

Потом:

```bash
cd bot
pip install -r requirements.txt
python -m iphone_bot.main
```

## Запуск через Docker

```bash
cd bot
cp .env.example .env
docker compose up -d --build
```

## GitHub Secrets для деплоя

В репозитории GitHub открой `Settings -> Secrets and variables -> Actions -> New repository secret` и добавь:

- `BOT_TOKEN` - токен Telegram-бота.
- `ADMIN_IDS` - твой Telegram ID.
- `SSH_HOST` - IP или домен сервера.
- `SSH_USER` - пользователь на сервере.
- `SSH_KEY` - приватный SSH-ключ для подключения к серверу.

Необязательные:

- `SSH_PORT` - SSH-порт, если не `22`.
- `DEPLOY_PATH` - папка на сервере, по умолчанию `/opt/iphone-bot`.

На сервере должен быть установлен Docker с `docker compose`.
