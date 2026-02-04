"""
Technical Indicators for Trading Signals
"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    from ta.trend import EMAIndicator, SMAIndicator, MACD
    from ta.momentum import RSIIndicator
    from ta.volatility import AverageTrueRange
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("ta library not installed. Technical indicators limited.")


class TechnicalIndicators:
    """Calculate technical indicators for trading signals"""
    
    def __init__(self, prices: pd.Series):
        """
        Args:
            prices: Series of closing prices with datetime index
        """
        self.prices = prices
        
    def ema(self, period: int = 20) -> pd.Series:
        """Exponential Moving Average"""
        if TA_AVAILABLE:
            return EMAIndicator(self.prices, window=period).ema_indicator()
        return self.prices.ewm(span=period, adjust=False).mean()
    
    def sma(self, period: int = 20) -> pd.Series:
        """Simple Moving Average"""
        if TA_AVAILABLE:
            return SMAIndicator(self.prices, window=period).sma_indicator()
        return self.prices.rolling(window=period).mean()
    
    def rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        if TA_AVAILABLE:
            return RSIIndicator(self.prices, window=period).rsi()
        # Simple RSI calculation
        delta = self.prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def atr(self, high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        if TA_AVAILABLE:
            return AverageTrueRange(high, low, self.prices, window=period).average_true_range()
        # Simple ATR calculation
        tr = pd.concat([
            high - low,
            abs(high - self.prices.shift()),
            abs(low - self.prices.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()


def detect_trend(prices: pd.Series, fast_period: int = 9, slow_period: int = 21) -> str:
    """
    Detect market trend using EMA crossover
    
    Returns:
        'bullish': Fast EMA > Slow EMA (uptrend)
        'bearish': Fast EMA < Slow EMA (downtrend)
        'neutral': EMAs are close (consolidation)
    """
    if len(prices) < slow_period:
        return "neutral"
    
    indicators = TechnicalIndicators(prices)
    fast_ema = indicators.ema(fast_period)
    slow_ema = indicators.ema(slow_period)
    
    # Get latest values
    fast_val = fast_ema.iloc[-1]
    slow_val = slow_ema.iloc[-1]
    
    # Calculate percentage difference
    diff_pct = ((fast_val - slow_val) / slow_val) * 100
    
    if diff_pct > 0.5:
        return "bullish"
    elif diff_pct < -0.5:
        return "bearish"
    else:
        return "neutral"


def get_trading_signals(prices: pd.Series) -> dict:
    """
    Generate trading signals based on multiple indicators
    
    Returns dict with:
        - trend: bullish/bearish/neutral
        - rsi: current RSI value
        - ema_9: 9-period EMA
        - ema_21: 21-period EMA
        - signal_strength: 0-100 (higher = stronger signal)
    """
    if len(prices) < 21:
        return {
            "trend": "neutral",
            "rsi": 50,
            "ema_9": prices.iloc[-1],
            "ema_21": prices.iloc[-1],
            "signal_strength": 0
        }
    
    indicators = TechnicalIndicators(prices)
    
    ema_9 = indicators.ema(9).iloc[-1]
    ema_21 = indicators.ema(21).iloc[-1]
    rsi = indicators.rsi(14).iloc[-1]
    
    trend = detect_trend(prices)
    
    # Calculate signal strength (0-100)
    signal_strength = 0
    
    # EMA alignment bonus
    if trend == "bullish":
        signal_strength += 30
        if rsi < 70:  # Not overbought
            signal_strength += 20
    elif trend == "bearish":
        signal_strength += 30
        if rsi > 30:  # Not oversold
            signal_strength += 20
    
    # RSI confirmation
    if 40 < rsi < 60:
        signal_strength += 10  # Neutral zone
    elif (trend == "bullish" and 50 < rsi < 70):
        signal_strength += 25  # Bullish RSI
    elif (trend == "bearish" and 30 < rsi < 50):
        signal_strength += 25  # Bearish RSI
    
    return {
        "trend": trend,
        "rsi": round(rsi, 2),
        "ema_9": round(ema_9, 2),
        "ema_21": round(ema_21, 2),
        "signal_strength": min(100, signal_strength)
    }
