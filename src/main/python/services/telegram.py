"""Telegram notification service for price alerts."""

import logging
from typing import List, Optional

import requests

from ..models import PriceAlert

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Service for sending alerts via Telegram bot."""

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize the Telegram notifier.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = requests.Session()

    def _make_request(self, method: str, data: dict) -> Optional[dict]:
        """Make a request to the Telegram API."""
        url = self.API_URL.format(token=self.bot_token, method=method)

        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API error: {result.get('description')}")
                return None

            return result

        except requests.RequestException as e:
            logger.error(f"Error sending Telegram request: {e}")
            return None

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message to the configured chat.

        Args:
            text: Message text
            parse_mode: Message parsing mode (HTML, Markdown, etc.)

        Returns:
            True if message was sent successfully
        """
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }

        result = self._make_request("sendMessage", data)
        return result is not None

    def send_alert(self, alert: PriceAlert) -> bool:
        """
        Send a price alert notification.

        Args:
            alert: PriceAlert object to send

        Returns:
            True if alert was sent successfully
        """
        message = alert.format_message()
        return self.send_message(message)

    def send_alerts_batch(self, alerts: List[PriceAlert], max_per_message: int = 5) -> int:
        """
        Send multiple alerts, batching if necessary.

        Args:
            alerts: List of alerts to send
            max_per_message: Maximum alerts to include in one message

        Returns:
            Number of successfully sent messages
        """
        if not alerts:
            return 0

        sent = 0

        # If few alerts, send individually
        if len(alerts) <= max_per_message:
            for alert in alerts:
                if self.send_alert(alert):
                    sent += 1
        else:
            # Batch into summary messages
            for i in range(0, len(alerts), max_per_message):
                batch = alerts[i:i + max_per_message]
                message = self._format_batch_message(batch)
                if self.send_message(message):
                    sent += 1

        return sent

    def _format_batch_message(self, alerts: List[PriceAlert]) -> str:
        """Format multiple alerts into a single message (HTML format)."""
        lines = ["🚨 <b>PRICE ALERTS SUMMARY</b>\n"]

        for alert in alerts:
            sign = "+" if alert.change_percent > 0 else ""
            emoji = alert.direction_emoji
            lines.append(
                f"{emoji} <a href=\"{alert.market.market_url}\">{alert.market.question[:50]}...</a>\n"
                f"   {alert.outcome}: {alert.old_price:.2f} → {alert.new_price:.2f} (<b>{sign}{alert.change_percent:.1f}%</b>)\n"
            )

        lines.append(f"\n📊 Total: {len(alerts)} market(s) with significant moves")

        return "\n".join(lines)

    def send_startup_message(self, market_count: int, threshold: float, volume_filter: float) -> bool:
        """
        Send a startup notification.

        Args:
            market_count: Number of markets being monitored
            threshold: Price change threshold percentage
            volume_filter: Minimum volume filter

        Returns:
            True if message was sent successfully
        """
        message = (
            "🚀 Polymarket Price Monitor Started\n\n"
            f"📊 Monitoring: {market_count:,} markets\n"
            f"📈 Alert threshold: {threshold}%\n"
            f"💰 Min volume: ${volume_filter:,.0f}\n\n"
            "You'll receive alerts when any market moves significantly."
        )
        return self.send_message(message)

    def send_status_message(self, market_count: int, alerts_sent: int, uptime_hours: float) -> bool:
        """
        Send a status update message.

        Args:
            market_count: Number of markets being monitored
            alerts_sent: Total alerts sent this session
            uptime_hours: Hours the monitor has been running

        Returns:
            True if message was sent successfully
        """
        message = (
            "📊 Polymarket Monitor Status\n\n"
            f"🕐 Uptime: {uptime_hours:.1f} hours\n"
            f"📈 Markets monitored: {market_count:,}\n"
            f"🔔 Alerts sent: {alerts_sent:,}\n"
        )
        return self.send_message(message)

    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection.

        Returns:
            True if connection is working
        """
        result = self._make_request("getMe", {})
        if result:
            bot_info = result.get("result", {})
            logger.info(f"Connected to Telegram bot: @{bot_info.get('username')}")
            return True
        return False
