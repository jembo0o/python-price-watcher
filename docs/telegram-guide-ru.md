# Telegram-бот для price-watcher

Теперь проект можно использовать одновременно через терминал и Telegram. Оба
интерфейса работают с одним `watchlist.json`; антиспам уведомлений хранится в
`state.json`.

## 0. Сначала обнови токен

Токен бота ранее был отправлен в чат открытым текстом. Считай его
скомпрометированным: открой `@BotFather`, отзови старый токен и выпусти новый.
Старый токен больше не используй и не добавляй в Git.

## 1. Подготовь окружение

В терминале из корня проекта:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Если `.env` уже существует, повторно копировать файл не нужно. Заполни его:

```dotenv
TELEGRAM_BOT_TOKEN=НОВЫЙ_ТОКЕН_ОТ_BOTFATHER
TELEGRAM_CHAT_ID=
CHECK_INTERVAL_SECONDS=3600
STEAM_REGION=eu
```

`STEAM_REGION` задает регион по умолчанию для команд бота. Доступны `us`, `ua`,
`eu` и обычные двухбуквенные коды стран Steam. Алиас `eu` использует немецкую
витрину Steam и цены в евро.

## 2. Получи chat ID

1. Открой своего бота в Telegram и отправь ему `/start`.
2. Убедись, что процесс `telegram bot` пока не запущен.
3. Выполни:

```bash
python -m price_watcher.cli telegram chat-id
```

Команда выведет число, например `123456789 [private]`. Запиши только число в
`.env`:

```dotenv
TELEGRAM_CHAT_ID=123456789
```

Этот ID одновременно является списком доступа: бот выполняет команды только из
указанного чата. На сообщения из других чатов он отвечает `Access denied`.

## 3. Проверь отправку

```bash
python -m price_watcher.cli telegram send-test \
  --message "Price Watcher подключен"
```

В Telegram должно прийти тестовое сообщение.

## 4. Запусти бота

```bash
python -m price_watcher.cli telegram bot
```

Оставь терминал открытым. Остановка: `Ctrl+C`.

Для быстрой локальной проверки можно уменьшить интервал:

```bash
python -m price_watcher.cli telegram bot --interval 60
```

В одном проекте должен работать только один процесс `telegram bot`. Если
запустить второй polling-процесс с тем же токеном, Telegram может вернуть ошибку
конфликта `getUpdates`.

## 5. Команды в Telegram

Поиск по названию:

```text
/search Elden Ring
/search region=ua Cyberpunk 2077
```

Цена по Steam App ID:

```text
/price 1245620
/price 1245620 region=eu
```

Добавление по названию или ID. Сначала указывается целевая цена:

```text
/add 29.99 Elden Ring
/add 29.99 region=eu Elden Ring
/add 29.99 region=us 1245620
```

Просмотр, ручная проверка и удаление:

```text
/list
/check
/remove 1245620
/remove 1245620 region=eu
```

Без `region=...` бот использует `STEAM_REGION` из `.env`. `/remove` без региона
удаляет игру для всех регионов.

## 6. Как приходят предупреждения

Процесс `telegram bot` не только отвечает на команды, но и автоматически
проверяет список через каждые `CHECK_INTERVAL_SECONDS`.

Уведомление отправляется, когда:

- текущая цена впервые стала меньше или равна целевой;
- после предыдущего уведомления цена упала еще ниже.

Одинаковая цена повторное сообщение не вызывает. Последняя уведомленная цена
хранится в `state.json`. Команда `/check` показывает состояние сейчас, но не
ломает антиспам и не помечает цену как уже уведомленную.

## 7. CLI продолжает работать

Пока бот запущен, можно пользоваться обычными командами в другом терминале:

```bash
python -m price_watcher.cli search --query "Elden Ring" --region eu
python -m price_watcher.cli watchlist add \
  --query "Elden Ring" --target-price 29.99 --region eu
python -m price_watcher.cli watchlist list
```

Telegram сразу увидит изменения при следующей команде или проверке, потому что
оба интерфейса используют один файл `watchlist.json`.

Не запускай одновременно `python -m price_watcher.cli watch --notify` и
`telegram bot`: это два независимых цикла проверки одной watchlist. Для режима с
Telegram достаточно `telegram bot`.

## 8. Запуск в PyCharm

1. Открой `Run | Edit Configurations`.
2. Нажми `+` и выбери `Python`.
3. Выбери вариант запуска `Module name`.
4. Module name: `price_watcher.cli`.
5. Parameters: `telegram bot`.
6. Working directory: корень проекта.
7. Python interpreter: `.venv/bin/python`.
8. Запусти конфигурацию и оставь окно Run открытым.

`python-dotenv` загрузит `.env` из корня проекта, поэтому токен не нужно вписывать
в параметры запуска PyCharm.

## 9. Проверка перед коммитом

```bash
python -m compileall price_watcher tests
python -m unittest
git status --short
git add .
git status --short
git commit -m "Add interactive Telegram price watcher bot"
git push
```

Файлы `.env`, `watchlist.json` и `state.json` уже находятся в `.gitignore` и не
должны попасть в коммит.

## 10. Почему архитектура подходит для сайта и расширения

`price_watcher/service.py` не знает ни о Telegram, ни об `argparse`. Он дает
обычные методы Python: получить цену, найти игры, добавить/удалить запись и
проверить watchlist.

Следующий архитектурный этап для сайта:

1. Добавить FastAPI как HTTP-обертку над `PriceWatcherService`.
2. Заменить JSON на SQLite/PostgreSQL и добавить пользователей.
3. Подключить сайт или браузерное расширение к HTTP API.
4. Запустить бот и API на сервере 24/7.

Расширение браузера не должно обращаться к Steam и хранить Telegram-токен само:
оно будет общаться только с нашим будущим API. Текущий сервисный слой позволяет
сделать это без переписывания логики поиска и цен.
