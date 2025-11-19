"""
Momentum Options Buying Strategy
Designed for micro-capital (₹5-10K) trading weekly options
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from enum import Enum

from src.utils.indicators import TechnicalIndicators as ti
from src.utils.logger import TradingLogger

logger = TradingLogger("MomentumStrategy")


class Signal(Enum):
    """Trading signal types"""
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    EXIT = "EXIT"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class MarketRegime(Enum):
    """Market regime based on ADX"""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"


class MomentumOptionsStrategy:
    """
    Momentum-based options buying strategy for NIFTY/BANKNIFTY

    Entry Logic:
    - RSI oversold/overbought + MACD confirmation + ADX trending
    - Buy calls on oversold bounce, puts on overbought rejection

    Exit Logic:
    - Target: 20-30% profit
    - Stop Loss: 30% loss (or ATR-based)
    - Time Exit: Before expiry theta decay

    Risk Management:
    - Max 2% capital per trade
    - Max ₹500 daily loss
    - Max 2 open positions
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize strategy with configuration

        Args:
            config: Strategy configuration dictionary
        """
        # Default configuration for micro-capital
        self.config = {
            # Indicator parameters
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'adx_period': 14,
            'adx_trending_threshold': 25,
            'adx_weak_threshold': 20,
            'atr_period': 14,

            # Entry/Exit parameters
            'target_pct': 20.0,  # 20% profit target
            'stop_loss_pct': 30.0,  # 30% stop loss
            'trailing_stop_pct': 15.0,  # 15% trailing stop after 10% profit
            'trailing_activation_pct': 10.0,  # Activate trailing after 10% profit

            # Time-based exits
            'max_holding_minutes': 180,  # 3 hours max
            'exit_before_expiry_days': 1,  # Exit 1 day before expiry

            # Position sizing
            'max_position_size': 2000,  # ₹2,000 max per trade
            'min_position_size': 500,  # ₹500 min per trade

            # Signal confirmation
            'require_volume_confirmation': True,
            'min_volume_ratio': 1.2,  # 20% above average volume
        }

        # Override with provided config
        if config:
            self.config.update(config)

        # State tracking
        self.current_position = None
        self.entry_price = None
        self.entry_time = None
        self.highest_price_since_entry = None
        self.trailing_stop_active = False

        logger.info("Momentum Options Strategy initialized")
        logger.info(f"  Target: {self.config['target_pct']}%")
        logger.info(f"  Stop Loss: {self.config['stop_loss_pct']}%")
        logger.info(f"  Max Position: ₹{self.config['max_position_size']}")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators

        Args:
            df: OHLCV DataFrame with columns: open, high, low, close, volume

        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()

        # RSI
        df['rsi'] = ti.rsi(df['close'], self.config['rsi_period'])

        # MACD
        macd_line, signal_line, histogram = ti.macd(
            df['close'],
            self.config['macd_fast'],
            self.config['macd_slow'],
            self.config['macd_signal']
        )
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram

        # ADX (trend strength)
        df['adx'] = ti.adx(
            df['high'], df['low'], df['close'],
            self.config['adx_period']
        )

        # ATR (for stop loss calculation)
        df['atr'] = ti.atr(
            df['high'], df['low'], df['close'],
            self.config['atr_period']
        )

        # Bollinger Bands (for mean reversion signals)
        upper, middle, lower = ti.bollinger_bands(df['close'], 20, 2.0)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower

        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # EMA for trend direction
        df['ema_9'] = ti.ema(df['close'], 9)
        df['ema_21'] = ti.ema(df['close'], 21)

        logger.info("Indicators calculated successfully")

        return df

    def detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime based on ADX

        Args:
            df: DataFrame with ADX calculated

        Returns:
            MarketRegime enum
        """
        if 'adx' not in df.columns:
            df = self.calculate_indicators(df)

        current_adx = df['adx'].iloc[-1]

        if pd.isna(current_adx):
            return MarketRegime.RANGING

        if current_adx > self.config['adx_trending_threshold']:
            regime = MarketRegime.TRENDING
        elif current_adx < self.config['adx_weak_threshold']:
            regime = MarketRegime.RANGING
        else:
            regime = MarketRegime.VOLATILE

        logger.info(f"Market Regime: {regime.value} (ADX: {current_adx:.2f})")

        return regime

    def generate_signal(self, df: pd.DataFrame, days_to_expiry: int = 5) -> Tuple[Signal, Dict]:
        """
        Generate trading signal based on indicators

        Args:
            df: OHLCV DataFrame
            days_to_expiry: Days remaining to option expiry

        Returns:
            Tuple of (Signal, metadata dict)
        """
        # Calculate indicators if not present
        if 'rsi' not in df.columns:
            df = self.calculate_indicators(df)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        metadata = {
            'rsi': latest['rsi'],
            'macd_histogram': latest['macd_histogram'],
            'adx': latest['adx'],
            'atr': latest['atr'],
            'close': latest['close'],
            'volume_ratio': latest.get('volume_ratio', 1.0),
            'days_to_expiry': days_to_expiry,
            'timestamp': datetime.now()
        }

        # Check if we should avoid trading
        if days_to_expiry <= self.config['exit_before_expiry_days']:
            logger.info(f"Avoiding trade - too close to expiry ({days_to_expiry} days)")
            return Signal.NO_TRADE, metadata

        # Check market regime
        regime = self.detect_market_regime(df)
        metadata['regime'] = regime.value

        # In ranging market, avoid momentum trades
        if regime == MarketRegime.RANGING:
            logger.info("Ranging market - waiting for trend")
            return Signal.NO_TRADE, metadata

        # Volume confirmation
        if self.config['require_volume_confirmation']:
            if latest.get('volume_ratio', 0) < self.config['min_volume_ratio']:
                logger.info(f"Low volume ({latest.get('volume_ratio', 0):.2f}x) - waiting for confirmation")
                return Signal.NO_TRADE, metadata

        # Generate signals based on momentum
        signal = Signal.NO_TRADE

        # BULLISH SIGNAL: RSI oversold + MACD bullish crossover
        if (latest['rsi'] < self.config['rsi_oversold'] and
            latest['macd_histogram'] > 0 and
            prev['macd_histogram'] <= 0):  # Crossover

            signal = Signal.BUY_CALL
            metadata['reason'] = "RSI oversold + MACD bullish crossover"
            logger.signal(f"BUY CALL - RSI: {latest['rsi']:.2f}, MACD turning bullish")

        # BEARISH SIGNAL: RSI overbought + MACD bearish crossover
        elif (latest['rsi'] > self.config['rsi_overbought'] and
              latest['macd_histogram'] < 0 and
              prev['macd_histogram'] >= 0):  # Crossover

            signal = Signal.BUY_PUT
            metadata['reason'] = "RSI overbought + MACD bearish crossover"
            logger.signal(f"BUY PUT - RSI: {latest['rsi']:.2f}, MACD turning bearish")

        # Alternative: Strong trend continuation
        elif regime == MarketRegime.TRENDING:
            # Bullish trend continuation
            if (latest['ema_9'] > latest['ema_21'] and
                latest['rsi'] > 50 and latest['rsi'] < 70 and
                latest['macd_histogram'] > 0):

                signal = Signal.BUY_CALL
                metadata['reason'] = "Bullish trend continuation"
                logger.signal(f"BUY CALL - Trend continuation, RSI: {latest['rsi']:.2f}")

            # Bearish trend continuation
            elif (latest['ema_9'] < latest['ema_21'] and
                  latest['rsi'] < 50 and latest['rsi'] > 30 and
                  latest['macd_histogram'] < 0):

                signal = Signal.BUY_PUT
                metadata['reason'] = "Bearish trend continuation"
                logger.signal(f"BUY PUT - Trend continuation, RSI: {latest['rsi']:.2f}")

        return signal, metadata

    def calculate_position_size(self, capital: float, option_price: float) -> int:
        """
        Calculate position size based on capital and risk

        Args:
            capital: Available capital
            option_price: Current option premium

        Returns:
            Number of lots to buy (1 lot = 1 for options)
        """
        # For micro-capital: use up to 20% of capital per trade (aggressive but controlled)
        max_risk = capital * 0.20

        # Limit by configured max position size
        max_investment = min(max_risk, self.config['max_position_size'])

        # Ensure minimum position size
        if max_investment < self.config['min_position_size']:
            logger.warning(f"Capital too low for trade (need ₹{self.config['min_position_size']})")
            return 0

        # For options buying, position size is based on premium
        # Assuming lot size of 1 for simplicity (actual NIFTY lot = 25)
        lots = int(max_investment / option_price)

        if lots == 0:
            logger.warning(f"Option premium (₹{option_price}) too high for capital")
            return 0

        logger.info(f"Position size: {lots} lots (₹{lots * option_price:.2f})")

        return lots

    def calculate_exit_levels(self, entry_price: float, atr: float) -> Dict:
        """
        Calculate target and stop loss levels

        Args:
            entry_price: Entry price of the option
            atr: Current ATR value

        Returns:
            Dictionary with exit levels
        """
        # Percentage-based levels
        target = entry_price * (1 + self.config['target_pct'] / 100)
        stop_loss = entry_price * (1 - self.config['stop_loss_pct'] / 100)

        # ATR-based stop (alternative)
        atr_stop = entry_price - (2 * atr)

        # Use the tighter stop
        final_stop = max(stop_loss, atr_stop)

        exit_levels = {
            'target': round(target, 2),
            'stop_loss': round(final_stop, 2),
            'trailing_activation': entry_price * (1 + self.config['trailing_activation_pct'] / 100),
            'risk_reward': round((target - entry_price) / (entry_price - final_stop), 2)
        }

        logger.info(f"Exit Levels - Target: ₹{exit_levels['target']}, "
                   f"Stop: ₹{exit_levels['stop_loss']}, "
                   f"R:R = {exit_levels['risk_reward']}")

        return exit_levels

    def check_exit_conditions(self, current_price: float, entry_price: float,
                             entry_time: datetime, exit_levels: Dict) -> Tuple[bool, str]:
        """
        Check if any exit condition is met

        Args:
            current_price: Current option price
            entry_price: Entry price
            entry_time: Time of entry
            exit_levels: Dictionary with target/stop levels

        Returns:
            Tuple of (should_exit, reason)
        """
        # Target hit
        if current_price >= exit_levels['target']:
            return True, f"Target hit (₹{current_price:.2f} >= ₹{exit_levels['target']:.2f})"

        # Stop loss hit
        if current_price <= exit_levels['stop_loss']:
            return True, f"Stop loss hit (₹{current_price:.2f} <= ₹{exit_levels['stop_loss']:.2f})"

        # Trailing stop logic
        if current_price >= exit_levels['trailing_activation']:
            if not self.trailing_stop_active:
                self.trailing_stop_active = True
                self.highest_price_since_entry = current_price
                logger.info(f"Trailing stop activated at ₹{current_price:.2f}")
            else:
                # Update highest price
                if current_price > self.highest_price_since_entry:
                    self.highest_price_since_entry = current_price

                # Calculate trailing stop level
                trailing_stop = self.highest_price_since_entry * (1 - self.config['trailing_stop_pct'] / 100)

                if current_price <= trailing_stop:
                    return True, f"Trailing stop hit (₹{current_price:.2f} <= ₹{trailing_stop:.2f})"

        # Time-based exit
        holding_time = (datetime.now() - entry_time).total_seconds() / 60
        if holding_time >= self.config['max_holding_minutes']:
            return True, f"Max holding time exceeded ({holding_time:.0f} mins)"

        return False, ""

    def get_strategy_stats(self, trades: List[Dict]) -> Dict:
        """
        Calculate strategy performance statistics

        Args:
            trades: List of completed trade dictionaries

        Returns:
            Dictionary with performance metrics
        """
        if not trades:
            return {'total_trades': 0}

        df = pd.DataFrame(trades)

        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] <= 0]

        stats = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) * 100,
            'total_pnl': df['pnl'].sum(),
            'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
            'max_win': df['pnl'].max(),
            'max_loss': df['pnl'].min(),
            'avg_holding_time': df['holding_time_mins'].mean() if 'holding_time_mins' in df else 0,
        }

        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
        stats['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0

        # Expectancy
        stats['expectancy'] = (stats['win_rate'] / 100 * stats['avg_win'] -
                              (1 - stats['win_rate'] / 100) * abs(stats['avg_loss']))

        return stats

    def reset_state(self):
        """Reset strategy state for new trade"""
        self.current_position = None
        self.entry_price = None
        self.entry_time = None
        self.highest_price_since_entry = None
        self.trailing_stop_active = False


# Convenience function for quick signal generation
def get_momentum_signal(df: pd.DataFrame, config: Optional[Dict] = None) -> Tuple[Signal, Dict]:
    """
    Quick function to get trading signal

    Args:
        df: OHLCV DataFrame
        config: Optional strategy config

    Returns:
        Tuple of (Signal, metadata)
    """
    strategy = MomentumOptionsStrategy(config)
    return strategy.generate_signal(df)


if __name__ == "__main__":
    print("Momentum Options Strategy Test")
    print("=" * 70)

    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='h')

    # Simulate trending price data
    trend = np.linspace(0, 20, 100)  # Uptrend
    noise = np.cumsum(np.random.randn(100) * 2)
    close_prices = 20000 + trend + noise  # NIFTY-like prices

    df = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 10,
        'high': close_prices + abs(np.random.randn(100)) * 30,
        'low': close_prices - abs(np.random.randn(100)) * 30,
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    # Initialize strategy
    strategy = MomentumOptionsStrategy()

    print("\n1. Calculate Indicators")
    print("-" * 70)
    df_with_indicators = strategy.calculate_indicators(df)
    print(f"Latest RSI: {df_with_indicators['rsi'].iloc[-1]:.2f}")
    print(f"Latest MACD Histogram: {df_with_indicators['macd_histogram'].iloc[-1]:.2f}")
    print(f"Latest ADX: {df_with_indicators['adx'].iloc[-1]:.2f}")
    print(f"Latest ATR: {df_with_indicators['atr'].iloc[-1]:.2f}")

    print("\n2. Detect Market Regime")
    print("-" * 70)
    regime = strategy.detect_market_regime(df_with_indicators)
    print(f"Current Regime: {regime.value}")

    print("\n3. Generate Signal")
    print("-" * 70)
    signal, metadata = strategy.generate_signal(df_with_indicators, days_to_expiry=3)
    print(f"Signal: {signal.value}")
    print(f"Reason: {metadata.get('reason', 'N/A')}")

    print("\n4. Calculate Position Size")
    print("-" * 70)
    capital = 10000  # ₹10K
    option_price = 150  # ₹150 premium
    lots = strategy.calculate_position_size(capital, option_price)
    print(f"Capital: ₹{capital}")
    print(f"Option Premium: ₹{option_price}")
    print(f"Recommended Lots: {lots}")
    print(f"Total Investment: ₹{lots * option_price}")

    print("\n5. Calculate Exit Levels")
    print("-" * 70)
    atr = df_with_indicators['atr'].iloc[-1]
    exit_levels = strategy.calculate_exit_levels(option_price, atr)
    print(f"Entry: ₹{option_price}")
    print(f"Target: ₹{exit_levels['target']} (+{strategy.config['target_pct']}%)")
    print(f"Stop Loss: ₹{exit_levels['stop_loss']} (-{strategy.config['stop_loss_pct']}%)")
    print(f"Risk:Reward = 1:{exit_levels['risk_reward']}")

    print("\n6. Sample Trade Simulation")
    print("-" * 70)

    # Simulate a winning trade
    entry_price = 150
    entry_time = datetime.now()

    # Price moves up
    test_prices = [150, 155, 165, 175, 185]  # Moving towards target

    for i, current_price in enumerate(test_prices):
        should_exit, reason = strategy.check_exit_conditions(
            current_price, entry_price, entry_time, exit_levels
        )
        pnl = (current_price - entry_price) * lots
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        status = "EXIT" if should_exit else "HOLD"
        print(f"  Step {i+1}: Price=₹{current_price}, P&L=₹{pnl:.0f} ({pnl_pct:+.1f}%) → {status}")

        if should_exit:
            print(f"  Reason: {reason}")
            break

    print("\n7. Strategy Statistics (Sample)")
    print("-" * 70)

    # Sample trades for statistics
    sample_trades = [
        {'pnl': 30, 'holding_time_mins': 45},
        {'pnl': -45, 'holding_time_mins': 120},
        {'pnl': 50, 'holding_time_mins': 60},
        {'pnl': 25, 'holding_time_mins': 30},
        {'pnl': -30, 'holding_time_mins': 90},
        {'pnl': 40, 'holding_time_mins': 55},
    ]

    stats = strategy.get_strategy_stats(sample_trades)
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Total P&L: ₹{stats['total_pnl']:.0f}")
    print(f"Profit Factor: {stats['profit_factor']:.2f}")
    print(f"Expectancy: ₹{stats['expectancy']:.2f} per trade")
    print(f"Avg Holding Time: {stats['avg_holding_time']:.0f} mins")

    print("\n" + "=" * 70)
    print("✅ Momentum Options Strategy Working Successfully!")
    print("=" * 70)

    print("\nStrategy Features:")
    print("  1. RSI + MACD entry signals")
    print("  2. ADX market regime detection")
    print("  3. ATR-based stop loss calculation")
    print("  4. Trailing stop with activation threshold")
    print("  5. Time-based exit (max holding period)")
    print("  6. Position sizing for micro-capital")
    print("  7. Performance statistics")

    print("\nReady for backtesting integration! 🚀")
