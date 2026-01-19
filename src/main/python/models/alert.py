"""Alert data model for price change alerts."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .market import Market


@dataclass
class PriceAlert:
    """Represents a price change alert for a market outcome."""

    market: "Market"
    outcome_index: int
    outcome: str
    old_price: float
    new_price: float
    change_percent: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def direction(self) -> str:
        """Get the direction of price change."""
        if self.change_percent > 0:
            return "up"
        elif self.change_percent < 0:
            return "down"
        return "unchanged"

    @property
    def direction_emoji(self) -> str:
        """Get emoji representing price direction."""
        if self.change_percent > 0:
            return "📈"
        elif self.change_percent < 0:
            return "📉"
        return "➡️"

    def format_message(self) -> str:
        """Format alert as a readable message."""
        sign = "+" if self.change_percent > 0 else ""
        return (
            f"🚨 PRICE ALERT\n\n"
            f"📊 {self.market.question}\n"
            f"{self.direction_emoji} Outcome: {self.outcome}\n"
            f"💰 Price: {self.old_price:.2f} → {self.new_price:.2f} ({sign}{self.change_percent:.1f}%)\n"
            f"📊 Volume: ${self.market.volume:,.0f}\n\n"
            f"🔗 {self.market.market_url}"
        )
