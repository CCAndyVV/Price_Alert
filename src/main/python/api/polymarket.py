"""Polymarket API client for fetching market data and prices."""

import logging
import time
from typing import List, Optional, Dict, Any

import requests

from ..models import Market

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Client for interacting with Polymarket APIs."""

    GAMMA_API_URL = "https://gamma-api.polymarket.com"
    CLOB_API_URL = "https://clob.polymarket.com"

    def __init__(self, page_size: int = 100, request_delay: float = 0.1):
        """
        Initialize the Polymarket client.

        Args:
            page_size: Number of markets to fetch per request
            request_delay: Delay between requests in seconds (rate limiting)
        """
        self.page_size = page_size
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PolymarketPriceMonitor/1.0"
        })

    def get_all_markets(self, min_volume: float = 0, active_only: bool = True) -> List[Market]:
        """
        Fetch all markets from the Gamma API with pagination.

        Args:
            min_volume: Minimum volume filter (USD)
            active_only: Only fetch active markets

        Returns:
            List of Market objects
        """
        markets = []
        offset = 0

        logger.info(f"Fetching all markets (min_volume=${min_volume:,.0f})...")

        while True:
            params = {
                "limit": self.page_size,
                "offset": offset,
                "active": str(active_only).lower(),
                "closed": "false",
            }

            try:
                response = self.session.get(
                    f"{self.GAMMA_API_URL}/markets",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                for market_data in data:
                    market = self._parse_market(market_data)
                    if market and market.volume >= min_volume:
                        markets.append(market)

                logger.debug(f"Fetched {len(data)} markets (offset={offset})")

                if len(data) < self.page_size:
                    break

                offset += self.page_size
                time.sleep(self.request_delay)

            except requests.RequestException as e:
                logger.error(f"Error fetching markets at offset {offset}: {e}")
                break

        logger.info(f"Found {len(markets)} markets matching criteria")
        return markets

    def _parse_market(self, data: Dict[str, Any]) -> Optional[Market]:
        """Parse market data from API response."""
        try:
            # Use market ID as primary identifier
            market_id = str(data.get("id", ""))
            if not market_id:
                return None

            # Get CLOB token IDs if available (for future CLOB API usage)
            clob_token_ids = data.get("clobTokenIds", [])

            # Parse outcomes and prices
            outcomes = data.get("outcomes", [])
            outcome_prices_str = data.get("outcomePrices", [])

            # Convert prices from strings to floats
            outcome_prices = []
            for price in outcome_prices_str:
                try:
                    outcome_prices.append(float(price))
                except (ValueError, TypeError):
                    outcome_prices.append(0.0)

            # Skip markets without valid prices
            if not outcome_prices or all(p == 0.0 for p in outcome_prices):
                return None

            # Get volume (prefer volumeNum for accuracy)
            volume = 0.0
            for vol_field in ["volumeNum", "volume", "volume24hr"]:
                if vol_field in data:
                    try:
                        volume = float(data[vol_field])
                        break
                    except (ValueError, TypeError):
                        continue

            return Market(
                token_id=market_id,
                condition_id=data.get("conditionId", ""),
                question=data.get("question", "Unknown"),
                slug=data.get("slug", ""),
                volume=volume,
                outcomes=outcomes if outcomes else ["Yes", "No"],
                outcome_prices=outcome_prices,
            )

        except Exception as e:
            logger.debug(f"Error parsing market data: {e}")
            return None

    def get_market_prices(self, market: Market) -> Optional[List[float]]:
        """
        Fetch current prices for a market from the CLOB API.

        Args:
            market: Market object to fetch prices for

        Returns:
            List of prices for each outcome, or None if failed
        """
        try:
            # The Gamma API already returns prices, so we can use those
            # For more accurate real-time prices, we could use CLOB
            # For now, re-fetch from Gamma for simplicity
            response = self.session.get(
                f"{self.GAMMA_API_URL}/markets",
                params={"slug": market.slug},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                market_data = data[0]
                outcome_prices_str = market_data.get("outcomePrices", [])
                prices = []
                for price in outcome_prices_str:
                    try:
                        prices.append(float(price))
                    except (ValueError, TypeError):
                        prices.append(0.0)
                return prices if prices else None

            return None

        except requests.RequestException as e:
            logger.debug(f"Error fetching prices for {market.slug}: {e}")
            return None

    def refresh_market_prices(self, markets: List[Market]) -> int:
        """
        Refresh prices for all markets.

        Args:
            markets: List of markets to refresh

        Returns:
            Number of successfully updated markets
        """
        updated = 0

        # Batch fetch all markets to minimize API calls
        all_market_data = {}
        offset = 0

        while True:
            try:
                response = self.session.get(
                    f"{self.GAMMA_API_URL}/markets",
                    params={
                        "limit": self.page_size,
                        "offset": offset,
                        "active": "true",
                        "closed": "false",
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                for market_data in data:
                    slug = market_data.get("slug", "")
                    if slug:
                        all_market_data[slug] = market_data

                if len(data) < self.page_size:
                    break

                offset += self.page_size
                time.sleep(self.request_delay)

            except requests.RequestException as e:
                logger.error(f"Error refreshing market data: {e}")
                break

        # Update prices for tracked markets
        for market in markets:
            if market.slug in all_market_data:
                market_data = all_market_data[market.slug]
                outcome_prices_str = market_data.get("outcomePrices", [])

                prices = []
                for price in outcome_prices_str:
                    try:
                        prices.append(float(price))
                    except (ValueError, TypeError):
                        prices.append(0.0)

                if prices:
                    market.update_prices(prices)
                    updated += 1

        return updated
