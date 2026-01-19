"""Price monitoring service for detecting significant price changes."""

import logging
from datetime import datetime
from typing import List, Optional

from ..api import PolymarketClient
from ..models import Market, PriceAlert

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Service for monitoring price changes across all Polymarket markets.

    Fetches all markets, stores baseline prices, and detects when
    prices change by more than the configured threshold.
    """

    def __init__(
        self,
        threshold_percent: float = 3.0,
        min_volume: float = 0,
        page_size: int = 100,
    ):
        """
        Initialize the price monitor.

        Args:
            threshold_percent: Minimum price change to trigger alert (e.g., 3.0 for 3%)
            min_volume: Minimum volume filter in USD
            page_size: Number of markets to fetch per API request
        """
        self.threshold_percent = threshold_percent
        self.min_volume = min_volume
        self.client = PolymarketClient(page_size=page_size)
        self.markets: List[Market] = []
        self.initialized = False
        self.last_scan_time: Optional[datetime] = None

    def initialize(self) -> int:
        """
        Initialize by fetching all markets and setting baseline prices.

        Returns:
            Number of markets loaded
        """
        logger.info("Initializing price monitor...")
        logger.info(f"Settings: threshold={self.threshold_percent}%, min_volume=${self.min_volume:,.0f}")

        self.markets = self.client.get_all_markets(min_volume=self.min_volume)
        self.last_scan_time = datetime.now()
        self.initialized = True

        logger.info(f"Loaded {len(self.markets)} markets for monitoring")
        return len(self.markets)

    def check_for_alerts(self) -> List[PriceAlert]:
        """
        Check all markets for price changes exceeding threshold.

        Returns:
            List of PriceAlert objects for markets with significant moves
        """
        if not self.initialized:
            logger.warning("Monitor not initialized. Call initialize() first.")
            return []

        logger.info("Checking prices for all markets...")

        # Refresh prices from API
        updated = self.client.refresh_market_prices(self.markets)
        logger.info(f"Updated prices for {updated} markets")

        # Check for significant changes
        alerts = []
        for market in self.markets:
            market_alerts = self._check_market(market)
            alerts.extend(market_alerts)

        if alerts:
            logger.info(f"Found {len(alerts)} price alerts")
        else:
            logger.debug("No significant price changes detected")

        self.last_scan_time = datetime.now()
        return alerts

    def _check_market(self, market: Market) -> List[PriceAlert]:
        """
        Check a single market for price changes.

        Args:
            market: Market to check

        Returns:
            List of alerts for this market (one per outcome with significant change)
        """
        alerts = []
        changes = market.get_price_changes()

        for i, (outcome, change) in enumerate(zip(market.outcomes, changes)):
            if abs(change) >= self.threshold_percent:
                alert = PriceAlert(
                    market=market,
                    outcome_index=i,
                    outcome=outcome,
                    old_price=market.baseline_prices[i],
                    new_price=market.outcome_prices[i],
                    change_percent=change,
                )
                alerts.append(alert)

        return alerts

    def reset_baselines(self, alerts: List[PriceAlert]) -> None:
        """
        Reset baseline prices for markets that triggered alerts.

        This prevents repeated alerts for the same price move.

        Args:
            alerts: List of alerts that were triggered
        """
        processed_markets = set()

        for alert in alerts:
            market_id = alert.market.token_id
            if market_id not in processed_markets:
                alert.market.reset_baseline()
                processed_markets.add(market_id)
                logger.debug(f"Reset baseline for: {alert.market.question[:50]}")

    def get_market_count(self) -> int:
        """Get the number of monitored markets."""
        return len(self.markets)

    def get_top_movers(self, limit: int = 10) -> List[PriceAlert]:
        """
        Get the top price movers regardless of threshold.

        Args:
            limit: Maximum number of movers to return

        Returns:
            List of top movers sorted by absolute change
        """
        all_changes = []

        for market in self.markets:
            changes = market.get_price_changes()
            for i, (outcome, change) in enumerate(zip(market.outcomes, changes)):
                if market.baseline_prices[i] > 0:  # Only include if we have a baseline
                    all_changes.append((market, i, outcome, change))

        # Sort by absolute change
        all_changes.sort(key=lambda x: abs(x[3]), reverse=True)

        # Convert to alerts
        alerts = []
        for market, i, outcome, change in all_changes[:limit]:
            alert = PriceAlert(
                market=market,
                outcome_index=i,
                outcome=outcome,
                old_price=market.baseline_prices[i],
                new_price=market.outcome_prices[i],
                change_percent=change,
            )
            alerts.append(alert)

        return alerts

    def refresh_markets(self) -> int:
        """
        Refresh the list of markets (picks up new markets).

        Returns:
            New total market count
        """
        logger.info("Refreshing market list...")

        # Get current market slugs for comparison
        existing_slugs = {m.slug for m in self.markets}

        # Fetch all markets
        new_markets = self.client.get_all_markets(min_volume=self.min_volume)
        new_slugs = {m.slug for m in new_markets}

        # Find newly added markets
        added_slugs = new_slugs - existing_slugs
        if added_slugs:
            logger.info(f"Found {len(added_slugs)} new markets")

        # Update markets list
        self.markets = new_markets

        return len(self.markets)
