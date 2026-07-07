# price-watcher

CLI utility for watching Steam product prices and preparing notifications when prices drop.

## Day 1

- Project structure
- Minimal dependencies
- Environment-based configuration

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Usage

Fetch one price:

```bash
python -m price_watcher.cli price --app-id 1245620 --region us
```

Add a game to the watchlist:

```bash
python -m price_watcher.cli watchlist add --app-id 1245620 --target-price 29.99 --region us
```

List saved games:

```bash
python -m price_watcher.cli watchlist list
```

Check the watchlist:

```bash
python -m price_watcher.cli watchlist check
```

Run continuous checks using `CHECK_INTERVAL_SECONDS` from `.env`:

```bash
python -m price_watcher.cli watch
```

Run continuous checks with Telegram notifications:

```bash
python -m price_watcher.cli watch --notify
```

Run two checks and stop:

```bash
python -m price_watcher.cli watch --max-runs 2
```

Send a Telegram notification when a target price is reached:

```bash
python -m price_watcher.cli watchlist check --notify
```

Find your Telegram chat ID after sending a message to the bot:

```bash
python -m price_watcher.cli telegram chat-id
```

Send a test Telegram message:

```bash
python -m price_watcher.cli telegram send-test
```
