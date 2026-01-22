"""Market data model for Polymarket markets."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Market:
    """Represents a Polymarket prediction market."""

    token_id: str
    condition_id: str
    question: str
    slug: str
    volume: float
    outcomes: List[str]
    outcome_prices: List[float]
    baseline_prices: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    market_url: Optional[str] = None
    event_slug: Optional[str] = None

    def __post_init__(self):
        """Set baseline prices if not provided."""
        if not self.baseline_prices:
            self.baseline_prices = self.outcome_prices.copy()
        # Use event_slug for URL (correct Polymarket link), fallback to market slug
        url_slug = self.event_slug or self.slug
        if not self.market_url and url_slug:
            self.market_url = f"https://polymarket.com/event/{url_slug}"

    def update_prices(self, new_prices: List[float]) -> None:
        """Update current prices."""
        self.outcome_prices = new_prices
        self.last_updated = datetime.now()

    def reset_baseline(self) -> None:
        """Reset baseline prices to current prices."""
        self.baseline_prices = self.outcome_prices.copy()

    def get_price_changes(self) -> List[float]:
        """Calculate percentage change from baseline for each outcome."""
        changes = []
        for i, (current, baseline) in enumerate(zip(self.outcome_prices, self.baseline_prices)):
            if baseline > 0:
                change = ((current - baseline) / baseline) * 100
            else:
                change = 0.0
            changes.append(change)
        return changes
