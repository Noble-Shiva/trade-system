"""
Market Data Fetcher - Fetch live and historical data
"""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from loguru import logger

try:
    from nsepython import nse_optionchain_scrapper, nse_eq, index_history
except ImportError:
    logger.warning("nsepython not installed. Some features may not work.")


class DataFetcher:
    """Fetch market data from NSE/BSE"""

    def __init__(self, broker=None):
        self.broker = broker

    def get_index_price(self, symbol: str) -> float:
        """Get current index price"""
        try:
            if self.broker and self.broker.is_authenticated:
                quote = self.broker.get_quote(symbol, "NSE")
                return quote.last_price

            # Fallback to NSE Python
            data = nse_eq(symbol)
            return data["priceInfo"]["lastPrice"]

        except Exception as e:
            logger.error(f"Error fetching index price for {symbol}: {e}")
            raise

    def get_option_chain(self, symbol: str) -> dict:
        """
        Get complete option chain with analysis

        Returns:
            dict with keys: spot_price, expiries, chain_data
        """
        try:
            if self.broker and self.broker.is_authenticated:
                # Get from broker
                expiries = self._get_expiries(symbol)
                if expiries:
                    return self.broker.get_option_chain(symbol, expiries[0])

            # Fallback to NSE scraper
            data = nse_optionchain_scrapper(symbol)

            return {
                "spot_price": data["records"]["underlyingValue"],
                "expiries": data["records"]["expiryDates"],
                "chain_data": data["records"]["data"]
            }

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            raise

    def _get_expiries(self, symbol: str) -> list:
        """Get list of expiry dates"""
        try:
            data = nse_optionchain_scrapper(symbol)
            return data["records"]["expiryDates"]
        except:
            return []

    def get_historical_data(
        self,
        symbol: str,
        days: int = 365,
        interval: str = "day"
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Index/stock symbol
            days: Number of days of history
            interval: 'day', '1minute', '5minute', '15minute'

        Returns:
            DataFrame with OHLCV data
        """
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            if self.broker and self.broker.is_authenticated:
                data = self.broker.get_historical_data(
                    symbol, "NSE", interval, from_date, to_date
                )
                return pd.DataFrame(data)

            # Fallback for daily data
            data = index_history(
                symbol,
                from_date.strftime("%d-%m-%Y"),
                to_date.strftime("%d-%m-%Y")
            )
            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise

    def get_vix(self) -> float:
        """Get India VIX value"""
        try:
            return self.get_index_price("INDIA VIX")
        except:
            return 15.0  # Default moderate VIX

    def calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calculate Average True Range for volatility"""
        try:
            df = self.get_historical_data(symbol, days=period * 2)

            if len(df) < period:
                return 0

            df['tr'] = pd.concat([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            ], axis=1).max(axis=1)

            return df['tr'].rolling(window=period).mean().iloc[-1]

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0
