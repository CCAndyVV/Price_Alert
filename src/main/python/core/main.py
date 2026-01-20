"""Main entry point for Polymarket Price Monitor."""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import click

from .config import Config, get_default_config_path
from ..services import PriceMonitor, TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class GracefulExit:
    """Handle graceful shutdown on SIGINT/SIGTERM."""

    def __init__(self):
        self.should_exit = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info("Received shutdown signal, exiting gracefully...")
        self.should_exit = True


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Polymarket Price Monitor - Monitor all markets for significant price changes."""
    pass


@cli.command()
@click.option("--threshold", "-t", default=3.0, help="Price change threshold percentage")
@click.option("--volume", "-v", default=0.0, help="Minimum volume filter (USD)")
@click.option("--interval", "-i", default=300, help="Poll interval in seconds")
@click.option("--config", "-c", default=None, help="Path to config file")
@click.option("--no-telegram", is_flag=True, help="Disable Telegram notifications (console only)")
def start(threshold: float, volume: float, interval: int, config: str, no_telegram: bool):
    """Start the price monitor."""
    logger.info("Starting Polymarket Price Monitor...")

    # Load configuration
    config_path = config or get_default_config_path()
    cfg = Config.load(config_path)

    # Override with CLI arguments
    cfg.price_change_threshold_percent = threshold
    cfg.min_volume_usd = volume
    cfg.poll_interval_seconds = interval
    if no_telegram:
        cfg.telegram_enabled = False

    # Validate configuration
    errors = cfg.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)

    logger.info(f"Configuration loaded: {cfg.to_dict()}")

    # Initialize Telegram notifier
    notifier = None
    if cfg.telegram_enabled:
        notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
        if not notifier.test_connection():
            logger.error("Failed to connect to Telegram. Check your bot token.")
            sys.exit(1)
        logger.info("Telegram connection successful")
    else:
        logger.info("Telegram disabled - alerts will be printed to console only")

    # Initialize price monitor
    monitor = PriceMonitor(
        threshold_percent=cfg.price_change_threshold_percent,
        min_volume=cfg.min_volume_usd,
        page_size=cfg.api_page_size,
    )

    market_count = monitor.initialize()

    if market_count == 0:
        logger.error("No markets found. Check your configuration.")
        sys.exit(1)

    # Send startup message
    if notifier:
        notifier.send_startup_message(
            market_count=market_count,
            threshold=cfg.price_change_threshold_percent,
            volume_filter=cfg.min_volume_usd,
        )

    # Main monitoring loop
    graceful_exit = GracefulExit()
    start_time = datetime.now()
    total_alerts_sent = 0

    logger.info(f"Monitoring {market_count} markets (checking every {cfg.poll_interval_seconds}s)...")

    while not graceful_exit.should_exit:
        try:
            # Check for price alerts
            alerts = monitor.check_for_alerts()

            if alerts:
                logger.info(f"Found {len(alerts)} alerts!")

                if notifier:
                    sent = notifier.send_alerts_batch(alerts)
                    total_alerts_sent += sent
                    logger.info(f"Sent {sent} alert(s) to Telegram")
                else:
                    # Print alerts to console when Telegram is disabled
                    click.echo(f"\n{'='*60}")
                    click.echo(f"PRICE ALERTS ({len(alerts)} markets)")
                    click.echo(f"{'='*60}\n")
                    for alert in alerts:
                        click.echo(alert.format_message())
                        click.echo("")
                    total_alerts_sent += len(alerts)

                # Reset baselines for alerted markets
                monitor.reset_baselines(alerts)
            else:
                logger.info("No significant price changes detected")

            # Wait for next check
            logger.info(f"Next check in {cfg.poll_interval_seconds} seconds...")

            # Sleep in small increments to allow graceful shutdown
            for _ in range(cfg.poll_interval_seconds):
                if graceful_exit.should_exit:
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            time.sleep(60)  # Wait a minute before retrying

    # Shutdown
    uptime = (datetime.now() - start_time).total_seconds() / 3600
    logger.info(f"Shutting down. Uptime: {uptime:.1f} hours, Alerts sent: {total_alerts_sent}")

    if notifier:
        notifier.send_status_message(
            market_count=market_count,
            alerts_sent=total_alerts_sent,
            uptime_hours=uptime,
        )


@cli.command()
@click.option("--config", "-c", default=None, help="Path to config file")
def test_telegram(config: str):
    """Test Telegram bot connection."""
    config_path = config or get_default_config_path()
    cfg = Config.load(config_path)

    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment")
        sys.exit(1)

    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)

    if notifier.test_connection():
        logger.info("Telegram connection successful!")

        # Send test message
        if notifier.send_message("🧪 Test message from Polymarket Price Monitor"):
            logger.info("Test message sent successfully!")
        else:
            logger.error("Failed to send test message")
    else:
        logger.error("Failed to connect to Telegram")
        sys.exit(1)


@cli.command()
@click.option("--threshold", "-t", default=3.0, help="Price change threshold percentage")
@click.option("--volume", "-v", default=0.0, help="Minimum volume filter (USD)")
@click.option("--limit", "-l", default=10, help="Number of top movers to show")
def top_movers(threshold: float, volume: float, limit: int):
    """Show current top price movers."""
    logger.info("Fetching top movers...")

    monitor = PriceMonitor(
        threshold_percent=threshold,
        min_volume=volume,
    )

    monitor.initialize()
    movers = monitor.get_top_movers(limit=limit)

    if not movers:
        logger.info("No price movements found")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"TOP {len(movers)} PRICE MOVERS")
    click.echo(f"{'='*60}\n")

    for i, alert in enumerate(movers, 1):
        sign = "+" if alert.change_percent > 0 else ""
        click.echo(f"{i}. {alert.market.question[:50]}...")
        click.echo(f"   {alert.outcome}: {alert.old_price:.2f} → {alert.new_price:.2f} ({sign}{alert.change_percent:.1f}%)")
        click.echo(f"   Volume: ${alert.market.volume:,.0f}")
        click.echo("")


@cli.command()
@click.option("--config", "-c", default=None, help="Path to config file")
def show_config(config: str):
    """Show current configuration."""
    config_path = config or get_default_config_path()
    cfg = Config.load(config_path)

    click.echo(f"\n{'='*40}")
    click.echo("CONFIGURATION")
    click.echo(f"{'='*40}\n")

    for key, value in cfg.to_dict().items():
        click.echo(f"{key}: {value}")

    click.echo(f"\nConfig file: {config_path}")
    click.echo(f"Telegram configured: {'Yes' if cfg.telegram_bot_token else 'No'}")


@cli.command()
@click.option("--volume", "-v", default=0.0, help="Minimum volume filter (USD)")
def count_markets(volume: float):
    """Count available markets."""
    from ..api import PolymarketClient

    logger.info(f"Counting markets with volume >= ${volume:,.0f}...")

    client = PolymarketClient()
    markets = client.get_all_markets(min_volume=volume)

    click.echo(f"\nTotal markets: {len(markets)}")

    if markets:
        total_volume = sum(m.volume for m in markets)
        click.echo(f"Combined volume: ${total_volume:,.0f}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
