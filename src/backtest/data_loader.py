"""
Historical Data Loader - Download and manage historical market data
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from loguru import logger

try:
    from jugaad_data.nse import stock_df, index_df
    from nsepython import nse_optionchain_scrapper, expiry_list
    JUGAAD_AVAILABLE = True
except ImportError:
    JUGAAD_AVAILABLE = False
    logger.warning("jugaad-data/nsepython not installed. Some features limited.")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class HistoricalDataLoader:
    """
    Download and manage historical data for backtesting

    Data sources:
    - NSE India (via nsepython)
    - Yahoo Finance (via yfinance)
    - Jugaad Data (for NSE historical)
    """

    def __init__(self, data_path: str = "data/historical"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def download_index_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        save: bool = True
    ) -> pd.DataFrame:
        """
        Download historical index data (NIFTY, BANKNIFTY, SENSEX)

        Args:
            symbol: Index symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            save: Save to CSV

        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Downloading {symbol} data from {start_date} to {end_date}")

        df = None

        # Try Jugaad Data first (best for NSE)
        if JUGAAD_AVAILABLE:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                # Map symbol to Jugaad format
                symbol_map = {
                    "NIFTY": "NIFTY 50",
                    "NIFTY50": "NIFTY 50",
                    "BANKNIFTY": "NIFTY BANK",
                    "NIFTYBANK": "NIFTY BANK",
                }
                jugaad_symbol = symbol_map.get(symbol.upper(), symbol)

                df = index_df(symbol=jugaad_symbol, from_date=start, to_date=end)
                df = df.rename(columns={
                    'HistoricalDate': 'date',
                    'OPEN': 'open',
                    'HIGH': 'high',
                    'LOW': 'low',
                    'CLOSE': 'close',
                    'VOLUME': 'volume'
                })
                logger.info(f"Downloaded {len(df)} rows from Jugaad Data")
            except Exception as e:
                logger.warning(f"Jugaad Data failed: {e}")

        # Fallback to Yahoo Finance
        if df is None and YFINANCE_AVAILABLE:
            try:
                # Map to Yahoo symbols
                yahoo_map = {
                    "NIFTY": "^NSEI",
                    "NIFTY50": "^NSEI",
                    "BANKNIFTY": "^NSEBANK",
                    "NIFTYBANK": "^NSEBANK",
                    "SENSEX": "^BSESN",
                }
                yahoo_symbol = yahoo_map.get(symbol.upper(), f"{symbol}.NS")

                ticker = yf.Ticker(yahoo_symbol)
                df = ticker.history(start=start_date, end=end_date)
                df = df.reset_index()
                df.columns = [c.lower() for c in df.columns]
                logger.info(f"Downloaded {len(df)} rows from Yahoo Finance")
            except Exception as e:
                logger.error(f"Yahoo Finance failed: {e}")

        if df is None or df.empty:
            raise ValueError(f"Could not download data for {symbol}")

        # Standardize columns
        df = self._standardize_dataframe(df)

        # Save to CSV
        if save:
            filepath = self.data_path / f"{symbol.lower()}_daily.csv"
            df.to_csv(filepath, index=False)
            logger.info(f"Saved to {filepath}")

        return df

    def download_option_chain_snapshot(
        self,
        symbol: str,
        save: bool = True
    ) -> dict:
        """
        Download current option chain snapshot

        Note: Historical option chain data is not freely available.
        This captures current snapshot for future backtesting.
        """
        if not JUGAAD_AVAILABLE:
            raise ImportError("nsepython required for option chain data")

        logger.info(f"Downloading option chain for {symbol}")

        try:
            data = nse_optionchain_scrapper(symbol)

            if save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = self.data_path / f"{symbol.lower()}_optionchain_{timestamp}.json"
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                logger.info(f"Saved option chain to {filepath}")

            return data

        except Exception as e:
            logger.error(f"Failed to download option chain: {e}")
            raise

    def generate_synthetic_option_data(
        self,
        index_data: pd.DataFrame,
        symbol: str,
        strike_interval: int = 50,
        num_strikes: int = 20
    ) -> pd.DataFrame:
        """
        Generate synthetic option data from index prices

        Since historical option data isn't freely available,
        we generate approximate option prices using Black-Scholes-like model.

        This is for backtesting only - not for live trading!
        """
        logger.info(f"Generating synthetic option data for {symbol}")

        from scipy.stats import norm
        import numpy as np

        records = []

        for idx, row in index_data.iterrows():
            spot = row['close']
            date = row['date']

            # ATM strike
            atm_strike = round(spot / strike_interval) * strike_interval

            # Generate strikes around ATM
            strikes = [atm_strike + (i - num_strikes//2) * strike_interval
                      for i in range(num_strikes)]

            for strike in strikes:
                if strike <= 0:
                    continue

                # Simplified option pricing (more realistic for Indian markets)
                # Weekly options typically have low premiums for OTM
                moneyness = spot / strike
                days_to_expiry = 7  # Assume weekly
                iv = 0.15  # 15% IV assumption

                # Calculate distance from ATM as percentage
                pct_from_atm = abs(spot - strike) / spot * 100

                # Base time value (scaled down for realistic premiums)
                base_time_value = spot * iv * np.sqrt(days_to_expiry / 365) * 0.1

                # Call premium
                if spot > strike:  # ITM
                    call_intrinsic = spot - strike
                    call_premium = call_intrinsic + base_time_value * 0.3
                else:  # OTM
                    # Exponential decay based on % OTM (realistic for weeklies)
                    decay = np.exp(-pct_from_atm * 0.8)
                    call_premium = max(5, base_time_value * decay)

                # Put premium
                if spot < strike:  # ITM
                    put_intrinsic = strike - spot
                    put_premium = put_intrinsic + base_time_value * 0.3
                else:  # OTM
                    # Exponential decay based on % OTM
                    decay = np.exp(-pct_from_atm * 0.8)
                    put_premium = max(5, base_time_value * decay)

                # Approximate OI based on distance from ATM
                distance = abs(strike - atm_strike) / strike_interval
                base_oi = 100000
                oi = int(base_oi * np.exp(-distance * 0.3))

                records.append({
                    'date': date,
                    'symbol': symbol,
                    'spot_price': spot,
                    'strike': strike,
                    'call_price': round(max(call_premium, 0.5), 2),
                    'put_price': round(max(put_premium, 0.5), 2),
                    'call_oi': oi,
                    'put_oi': oi,
                    'iv': iv
                })

        df = pd.DataFrame(records)

        # Save
        filepath = self.data_path / f"{symbol.lower()}_options_synthetic.csv"
        df.to_csv(filepath, index=False)
        logger.info(f"Generated {len(df)} option records, saved to {filepath}")

        return df

    def load_index_data(self, symbol: str) -> pd.DataFrame:
        """Load previously downloaded index data"""
        filepath = self.data_path / f"{symbol.lower()}_daily.csv"

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        return df

    def load_option_data(self, symbol: str) -> pd.DataFrame:
        """Load option data (synthetic or real)"""
        # Try synthetic first
        filepath = self.data_path / f"{symbol.lower()}_options_synthetic.csv"

        if not filepath.exists():
            raise FileNotFoundError(f"Option data not found: {filepath}")

        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        return df

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize DataFrame columns"""
        # Ensure required columns exist
        required = ['date', 'open', 'high', 'low', 'close']

        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            df['date'] = pd.to_datetime(df['Date'])
            df = df.drop('Date', axis=1)

        # Add volume if missing
        if 'volume' not in df.columns:
            df['volume'] = 0

        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)

        return df

    def get_available_data(self) -> list[str]:
        """List available data files"""
        files = list(self.data_path.glob("*.csv"))
        return [f.stem for f in files]

    def get_date_range(self, symbol: str) -> tuple[str, str]:
        """Get date range of available data"""
        df = self.load_index_data(symbol)
        return (
            df['date'].min().strftime("%Y-%m-%d"),
            df['date'].max().strftime("%Y-%m-%d")
        )
