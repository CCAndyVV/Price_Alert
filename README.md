# Polymarket Price Monitor

Monitor all Polymarket prediction markets for significant price changes and receive Telegram alerts.

## Features

- Monitor ALL active markets on Polymarket
- Configurable price change threshold (default: 3%)
- Configurable volume filter
- Telegram notifications for price alerts
- View top movers across all markets

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Telegram Bot

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Copy your bot token
3. Send a message to your bot, then get your chat ID from:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run the Monitor

```bash
# Start monitoring with defaults (3% threshold, all markets, 5 min interval)
python -m src.main.python start

# Custom settings
python -m src.main.python start --threshold 5 --volume 50000 --interval 300

# Test Telegram connection
python -m src.main.python test-telegram

# View top movers
python -m src.main.python top-movers --limit 20

# Count available markets
python -m src.main.python count-markets --volume 10000

# Show configuration
python -m src.main.python show-config
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `start` | Start the price monitor |
| `test-telegram` | Test Telegram bot connection |
| `top-movers` | Show current top price movers |
| `count-markets` | Count available markets |
| `show-config` | Display current configuration |

## Configuration

Edit `src/main/resources/config/settings.yaml`:

```yaml
monitoring:
  poll_interval_seconds: 300  # Check every 5 minutes
  price_change_threshold_percent: 3.0  # Alert on 3%+ changes
  min_volume_usd: 0  # Monitor all markets

telegram:
  enabled: true

api:
  page_size: 100
```

## Project Structure

```
Price_Alert/
├── src/main/python/
│   ├── api/              # Polymarket API client
│   ├── models/           # Data models (Market, PriceAlert)
│   ├── services/         # Price monitor, Telegram notifier
│   └── core/             # Main entry point, config
├── src/main/resources/
│   └── config/           # settings.yaml
├── requirements.txt
└── .env                  # Telegram credentials (create from .env.example)
```

## Alert Format

When a market moves by more than the threshold, you'll receive:

```
🚨 PRICE ALERT

📊 Will Trump win the 2024 election?
📈 Outcome: Yes
💰 Price: 0.45 → 0.52 (+15.6%)
📊 Volume: $125,000

🔗 https://polymarket.com/event/...
```

## License

MIT
