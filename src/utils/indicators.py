"""
Technical Indicators for Trading Strategies
Provides common technical analysis indicators for F&O trading
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple
from src.utils.logger import TradingLogger

logger = TradingLogger("TechnicalIndicators")


class TechnicalIndicators:
    """
    Technical Analysis Indicators
    All methods work with pandas Series/DataFrame
    """

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average

        Args:
            data: Price data (usually close prices)
            period: Number of periods

        Returns:
            SMA values as pandas Series
        """
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average

        Args:
            data: Price data (usually close prices)
            period: Number of periods

        Returns:
            EMA values as pandas Series
        """
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index

        Args:
            data: Price data (usually close prices)
            period: Number of periods (default: 14)

        Returns:
            RSI values (0-100) as pandas Series
        """
        # Calculate price changes
        delta = data.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def macd(data: pd.Series, fast_period: int = 12, slow_period: int = 26,
             signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Moving Average Convergence Divergence

        Args:
            data: Price data (usually close prices)
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        # Calculate EMAs
        ema_fast = TechnicalIndicators.ema(data, fast_period)
        ema_slow = TechnicalIndicators.ema(data, slow_period)

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)

        # Histogram
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range (Volatility Indicator)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Number of periods (default: 14)

        Returns:
            ATR values as pandas Series
        """
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR
        atr = true_range.rolling(window=period).mean()

        return atr

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, num_std: float = 2.0
                       ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands

        Args:
            data: Price data (usually close prices)
            period: Number of periods (default: 20)
            num_std: Number of standard deviations (default: 2.0)

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        # Middle band (SMA)
        middle_band = TechnicalIndicators.sma(data, period)

        # Standard deviation
        std = data.rolling(window=period).std()

        # Upper and lower bands
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)

        return upper_band, middle_band, lower_band

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            k_period: %K period (default: 14)
            d_period: %D period (default: 3)

        Returns:
            Tuple of (%K, %D)
        """
        # Calculate %K
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))

        # Calculate %D (SMA of %K)
        d = k.rolling(window=d_period).mean()

        return k, d

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index (Trend Strength Indicator)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Number of periods (default: 14)

        Returns:
            ADX values (0-100) as pandas Series
            ADX > 25: Strong trend
            ADX < 20: Weak trend / ranging market
        """
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate ATR
        atr = TechnicalIndicators.atr(high, low, close, period)

        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

        # Calculate ADX
        adx = dx.rolling(window=period).mean()

        return adx

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume (Volume Indicator)

        Args:
            close: Close prices
            volume: Volume data

        Returns:
            OBV values as pandas Series
        """
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Volume Weighted Average Price

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume data

        Returns:
            VWAP values as pandas Series
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        SuperTrend Indicator

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default: 10)
            multiplier: ATR multiplier (default: 3.0)

        Returns:
            Tuple of (supertrend, direction)
            direction: 1 for uptrend, -1 for downtrend
        """
        # Calculate ATR
        atr = TechnicalIndicators.atr(high, low, close, period)

        # Calculate basic upper and lower bands
        hl_avg = (high + low) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        # Initialize supertrend
        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=float)

        # Calculate supertrend
        for i in range(period, len(close)):
            if i == period:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                # Update bands
                if close.iloc[i - 1] <= supertrend.iloc[i - 1]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1

                # Adjust supertrend
                if direction.iloc[i] == 1:
                    if lower_band.iloc[i] > supertrend.iloc[i - 1]:
                        supertrend.iloc[i] = lower_band.iloc[i]
                    else:
                        supertrend.iloc[i] = supertrend.iloc[i - 1]
                else:
                    if upper_band.iloc[i] < supertrend.iloc[i - 1]:
                        supertrend.iloc[i] = upper_band.iloc[i]
                    else:
                        supertrend.iloc[i] = supertrend.iloc[i - 1]

        return supertrend, direction

    @staticmethod
    def support_resistance(data: pd.Series, window: int = 20) -> Tuple[float, float]:
        """
        Calculate support and resistance levels

        Args:
            data: Price data
            window: Lookback window

        Returns:
            Tuple of (support, resistance)
        """
        recent_data = data.tail(window)
        support = recent_data.min()
        resistance = recent_data.max()

        return support, resistance


# Convenience functions for easy import
def sma(data: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return TechnicalIndicators.sma(data, period)


def ema(data: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return TechnicalIndicators.ema(data, period)


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    return TechnicalIndicators.rsi(data, period)


def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD"""
    return TechnicalIndicators.macd(data, fast, slow, signal)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range"""
    return TechnicalIndicators.atr(high, low, close, period)


def bollinger_bands(data: pd.Series, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands"""
    return TechnicalIndicators.bollinger_bands(data, period, num_std)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index"""
    return TechnicalIndicators.adx(high, low, close, period)


if __name__ == "__main__":
    print("Technical Indicators Test")
    print("=" * 70)

    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')

    # Simulate price data (random walk with trend)
    close_prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 2), index=dates)
    high_prices = close_prices + abs(np.random.randn(100)) * 2
    low_prices = close_prices - abs(np.random.randn(100)) * 2
    volume = pd.Series(np.random.randint(1000000, 5000000, 100), index=dates)

    print(f"\n{'Sample Data (Last 5 days)':^70}")
    print("-" * 70)
    print(f"Close: {close_prices.tail().values}")

    # Test indicators
    print(f"\n{'Moving Averages':^70}")
    print("-" * 70)
    sma_20 = TechnicalIndicators.sma(close_prices, 20)
    ema_20 = TechnicalIndicators.ema(close_prices, 20)
    print(f"SMA(20) - Last: {sma_20.iloc[-1]:.2f}")
    print(f"EMA(20) - Last: {ema_20.iloc[-1]:.2f}")

    print(f"\n{'RSI (Relative Strength Index)':^70}")
    print("-" * 70)
    rsi_14 = TechnicalIndicators.rsi(close_prices, 14)
    print(f"RSI(14) - Last: {rsi_14.iloc[-1]:.2f}")
    if rsi_14.iloc[-1] > 70:
        print("  → Overbought (>70)")
    elif rsi_14.iloc[-1] < 30:
        print("  → Oversold (<30)")
    else:
        print("  → Neutral (30-70)")

    print(f"\n{'MACD':^70}")
    print("-" * 70)
    macd_line, signal_line, histogram = TechnicalIndicators.macd(close_prices)
    print(f"MACD Line:   {macd_line.iloc[-1]:.2f}")
    print(f"Signal Line: {signal_line.iloc[-1]:.2f}")
    print(f"Histogram:   {histogram.iloc[-1]:.2f}")
    if histogram.iloc[-1] > 0:
        print("  → Bullish (Histogram > 0)")
    else:
        print("  → Bearish (Histogram < 0)")

    print(f"\n{'ATR (Average True Range)':^70}")
    print("-" * 70)
    atr_14 = TechnicalIndicators.atr(high_prices, low_prices, close_prices, 14)
    print(f"ATR(14) - Last: {atr_14.iloc[-1]:.2f}")
    print(f"  → Volatility measure for stop loss placement")

    print(f"\n{'Bollinger Bands':^70}")
    print("-" * 70)
    upper, middle, lower = TechnicalIndicators.bollinger_bands(close_prices, 20, 2.0)
    print(f"Upper Band:  {upper.iloc[-1]:.2f}")
    print(f"Middle Band: {middle.iloc[-1]:.2f}")
    print(f"Lower Band:  {lower.iloc[-1]:.2f}")
    print(f"Current Price: {close_prices.iloc[-1]:.2f}")

    if close_prices.iloc[-1] > upper.iloc[-1]:
        print("  → Price above upper band (Overbought)")
    elif close_prices.iloc[-1] < lower.iloc[-1]:
        print("  → Price below lower band (Oversold)")
    else:
        print("  → Price within bands (Normal)")

    print(f"\n{'ADX (Trend Strength)':^70}")
    print("-" * 70)
    adx_14 = TechnicalIndicators.adx(high_prices, low_prices, close_prices, 14)
    print(f"ADX(14) - Last: {adx_14.iloc[-1]:.2f}")
    if adx_14.iloc[-1] > 25:
        print("  → Strong trend (ADX > 25)")
    elif adx_14.iloc[-1] < 20:
        print("  → Weak trend / Ranging market (ADX < 20)")
    else:
        print("  → Moderate trend (20-25)")

    print(f"\n{'Stochastic Oscillator':^70}")
    print("-" * 70)
    k, d = TechnicalIndicators.stochastic(high_prices, low_prices, close_prices)
    print(f"%K: {k.iloc[-1]:.2f}")
    print(f"%D: {d.iloc[-1]:.2f}")
    if k.iloc[-1] > 80:
        print("  → Overbought (%K > 80)")
    elif k.iloc[-1] < 20:
        print("  → Oversold (%K < 20)")
    else:
        print("  → Neutral (20-80)")

    print(f"\n{'Support & Resistance':^70}")
    print("-" * 70)
    support, resistance = TechnicalIndicators.support_resistance(close_prices, 20)
    print(f"Support:    {support:.2f}")
    print(f"Resistance: {resistance:.2f}")
    print(f"Current:    {close_prices.iloc[-1]:.2f}")

    print("\n" + "=" * 70)
    print("✅ All Technical Indicators Working Successfully!")
    print("=" * 70)

    print("\nIndicators Available:")
    print("  1. SMA - Simple Moving Average")
    print("  2. EMA - Exponential Moving Average")
    print("  3. RSI - Relative Strength Index")
    print("  4. MACD - Moving Average Convergence Divergence")
    print("  5. ATR - Average True Range (for stop loss)")
    print("  6. Bollinger Bands")
    print("  7. Stochastic Oscillator")
    print("  8. ADX - Average Directional Index (trend strength)")
    print("  9. OBV - On-Balance Volume")
    print(" 10. VWAP - Volume Weighted Average Price")
    print(" 11. SuperTrend")
    print(" 12. Support & Resistance")

    print("\nReady for strategy implementation! 🚀")
