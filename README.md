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
