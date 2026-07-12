# price-watcher

Personal Steam price tracker with two interfaces:

- CLI for search, price checks, and watchlist management;
- Telegram bot with the same operations and automatic price-drop alerts.

Both interfaces use `PriceWatcherService`, `watchlist.json`, and `state.json`.
The service is independent from Telegram and `argparse`, so it can later be
wrapped by FastAPI for a website or browser extension.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=your_new_bot_token
TELEGRAM_CHAT_ID=your_chat_id
CHECK_INTERVAL_SECONDS=3600
STEAM_REGION=eu
```

The full Telegram and PyCharm setup is in
[docs/telegram-guide-ru.md](docs/telegram-guide-ru.md).

## Telegram bot

```bash
python -m price_watcher.cli telegram chat-id
python -m price_watcher.cli telegram send-test
python -m price_watcher.cli telegram bot
```

Telegram commands:

```text
/search Elden Ring
/search region=ua Elden Ring
/price 1245620 region=eu
/add 29.99 region=eu Elden Ring
/list
/remove 1245620 region=eu
/check
```

`telegram bot` performs automatic checks using `CHECK_INTERVAL_SECONDS`. It
sends an alert only when a target is reached for the first time, or when the
price falls below the price from the previous alert.

## CLI

```bash
python -m price_watcher.cli search --query "elden ring" --region eu
python -m price_watcher.cli price --app-id 1245620 --region eu
python -m price_watcher.cli watchlist add --query "elden ring" --target-price 29.99 --region eu
python -m price_watcher.cli watchlist list
python -m price_watcher.cli watchlist check
python -m price_watcher.cli watchlist remove --app-id 1245620 --region eu
python -m price_watcher.cli watch --notify
```

Regions use Steam country codes. `ua` selects Ukraine. `eu` is a convenience
alias that currently uses Germany's euro storefront.

## Tests

```bash
python -m unittest
```

## Architecture

```text
CLI (cli.py) ---------+
                     +--> PriceWatcherService --> Steam client
Telegram bot --------+             |
                                   +--> watchlist.json
                                   +--> state.json
                                   +--> price checker
```

`watchlist.json`, `state.json`, and `.env` are local runtime files and are not
committed to Git.
