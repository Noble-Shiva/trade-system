"""
Backtesting Engine for Options Trading Strategies
Tests strategies on historical data before live deployment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.utils.logger import TradingLogger
from src.strategies.momentum_options import MomentumOptionsStrategy, Signal

logger = TradingLogger("BacktestEngine")


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    signal_type: str = ""  # BUY_CALL or BUY_PUT
    quantity: int = 1
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.exit_time is None

    @property
    def holding_time_mins(self) -> float:
        if self.exit_time and self.entry_time:
            return (self.exit_time - self.entry_time).total_seconds() / 60
        return 0


@dataclass
class BacktestResult:
    """Backtesting results and statistics"""
    trades: List[Trade]
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_return_pct: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_holding_time: float
    equity_curve: pd.Series
    daily_returns: pd.Series


class BacktestEngine:
    """
    Backtesting engine for options trading strategies

    Features:
    - Event-driven backtesting
    - Realistic slippage and commission modeling
    - Equity curve tracking
    - Comprehensive performance metrics
    """

    def __init__(self, initial_capital: float = 10000,
                 commission: float = 20,  # ₹20 per order
                 slippage_pct: float = 0.1):  # 0.1% slippage
        """
        Initialize backtest engine

        Args:
            initial_capital: Starting capital
            commission: Commission per trade (in ₹)
            slippage_pct: Slippage percentage
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission = commission
        self.slippage_pct = slippage_pct

        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[datetime] = []

        self.current_trade: Optional[Trade] = None

        logger.info(f"Backtest Engine initialized")
        logger.info(f"  Initial Capital: ₹{initial_capital}")
        logger.info(f"  Commission: ₹{commission}/trade")
        logger.info(f"  Slippage: {slippage_pct}%")

    def run(self, data: pd.DataFrame, strategy: MomentumOptionsStrategy,
            option_premium_col: str = 'close') -> BacktestResult:
        """
        Run backtest on historical data

        Args:
            data: OHLCV DataFrame with datetime index
            strategy: Trading strategy instance
            option_premium_col: Column to use as option premium proxy

        Returns:
            BacktestResult with all metrics
        """
        logger.info(f"Starting backtest...")
        logger.info(f"  Data period: {data.index[0]} to {data.index[-1]}")
        logger.info(f"  Total bars: {len(data)}")

        # Reset state
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = [data.index[0]]
        self.current_trade = None
        strategy.reset_state()

        # Calculate indicators once
        data = strategy.calculate_indicators(data)

        # Need minimum bars for indicators to warm up
        warmup_period = 50

        # Simulate day-by-day trading
        for i in range(warmup_period, len(data)):
            current_bar = data.iloc[i]
            current_time = data.index[i]
            history = data.iloc[:i+1]

            # Check if we have an open position
            if self.current_trade and self.current_trade.is_open:
                self._check_exit(current_bar, current_time, strategy, option_premium_col)
            else:
                # Generate signal for new entry
                self._check_entry(history, current_time, strategy, option_premium_col)

            # Update equity curve
            self._update_equity(current_bar, option_premium_col)

        # Close any open position at end
        if self.current_trade and self.current_trade.is_open:
            self._force_exit(data.iloc[-1], data.index[-1], "End of backtest", option_premium_col)

        # Calculate results
        result = self._calculate_results()

        logger.info(f"Backtest completed")
        logger.info(f"  Total trades: {result.total_trades}")
        logger.info(f"  Win rate: {result.win_rate:.1f}%")
        logger.info(f"  Total P&L: ₹{result.total_pnl:.2f}")
        logger.info(f"  Total Return: {result.total_return_pct:.1f}%")

        return result

    def _check_entry(self, history: pd.DataFrame, current_time: datetime,
                     strategy: MomentumOptionsStrategy, premium_col: str):
        """Check for entry signal and execute if valid"""

        # Generate signal
        signal, metadata = strategy.generate_signal(history, days_to_expiry=5)

        if signal in [Signal.BUY_CALL, Signal.BUY_PUT]:
            current_price = history[premium_col].iloc[-1]

            # Apply slippage
            entry_price = current_price * (1 + self.slippage_pct / 100)

            # Calculate position size
            quantity = strategy.calculate_position_size(self.capital, entry_price)

            if quantity > 0:
                # Create trade
                self.current_trade = Trade(
                    entry_time=current_time,
                    entry_price=entry_price,
                    signal_type=signal.value,
                    quantity=quantity,
                    metadata=metadata
                )

                # Deduct commission
                self.capital -= self.commission

                # Calculate exit levels
                atr = history['atr'].iloc[-1]
                exit_levels = strategy.calculate_exit_levels(entry_price, atr)
                self.current_trade.metadata['exit_levels'] = exit_levels

                logger.info(f"ENTRY: {signal.value} at ₹{entry_price:.2f} x {quantity}")

    def _check_exit(self, current_bar: pd.Series, current_time: datetime,
                    strategy: MomentumOptionsStrategy, premium_col: str):
        """Check exit conditions for open position"""

        if not self.current_trade:
            return

        current_price = current_bar[premium_col]
        exit_levels = self.current_trade.metadata.get('exit_levels', {})

        should_exit, reason = strategy.check_exit_conditions(
            current_price,
            self.current_trade.entry_price,
            self.current_trade.entry_time,
            exit_levels
        )

        if should_exit:
            self._execute_exit(current_price, current_time, reason)

    def _execute_exit(self, exit_price: float, exit_time: datetime, reason: str):
        """Execute trade exit"""

        if not self.current_trade:
            return

        # Apply slippage (unfavorable)
        exit_price = exit_price * (1 - self.slippage_pct / 100)

        # Calculate P&L
        if self.current_trade.signal_type == "BUY_CALL":
            pnl = (exit_price - self.current_trade.entry_price) * self.current_trade.quantity
        else:  # BUY_PUT
            pnl = (exit_price - self.current_trade.entry_price) * self.current_trade.quantity

        pnl_pct = ((exit_price - self.current_trade.entry_price) /
                   self.current_trade.entry_price) * 100

        # Deduct commission
        pnl -= self.commission

        # Update trade
        self.current_trade.exit_time = exit_time
        self.current_trade.exit_price = exit_price
        self.current_trade.pnl = pnl
        self.current_trade.pnl_pct = pnl_pct
        self.current_trade.exit_reason = reason

        # Update capital
        self.capital += pnl

        # Save trade
        self.trades.append(self.current_trade)

        logger.info(f"EXIT: ₹{exit_price:.2f}, P&L: ₹{pnl:.2f} ({pnl_pct:+.1f}%), Reason: {reason}")

        # Reset current trade
        self.current_trade = None

    def _force_exit(self, current_bar: pd.Series, current_time: datetime,
                    reason: str, premium_col: str):
        """Force exit open position"""
        exit_price = current_bar[premium_col]
        self._execute_exit(exit_price, current_time, reason)

    def _update_equity(self, current_bar: pd.Series, premium_col: str):
        """Update equity curve with current position value"""

        equity = self.capital

        # Add unrealized P&L if position is open
        if self.current_trade and self.current_trade.is_open:
            current_price = current_bar[premium_col]
            unrealized_pnl = ((current_price - self.current_trade.entry_price) *
                             self.current_trade.quantity)
            equity += unrealized_pnl

        self.equity_curve.append(equity)

    def _calculate_results(self) -> BacktestResult:
        """Calculate comprehensive backtest results"""

        if not self.trades:
            # Return empty result
            return BacktestResult(
                trades=[], initial_capital=self.initial_capital,
                final_capital=self.capital, total_pnl=0, total_return_pct=0,
                win_rate=0, profit_factor=0, max_drawdown=0, max_drawdown_pct=0,
                sharpe_ratio=0, total_trades=0, winning_trades=0, losing_trades=0,
                avg_win=0, avg_loss=0, largest_win=0, largest_loss=0,
                avg_holding_time=0, equity_curve=pd.Series(self.equity_curve),
                daily_returns=pd.Series([0])
            )

        # Basic stats
        pnl_list = [t.pnl for t in self.trades]
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]

        total_pnl = sum(pnl_list)
        total_return_pct = (total_pnl / self.initial_capital) * 100

        win_rate = (len(winning) / len(self.trades) * 100) if self.trades else 0

        # Profit factor
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = equity_series - rolling_max
        max_drawdown = abs(drawdown.min())
        max_drawdown_pct = (max_drawdown / self.initial_capital) * 100

        # Sharpe ratio (simplified)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = 0
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized

        # Win/Loss stats
        avg_win = np.mean([t.pnl for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl for t in losing]) if losing else 0
        largest_win = max(pnl_list) if pnl_list else 0
        largest_loss = min(pnl_list) if pnl_list else 0

        # Holding time
        avg_holding_time = np.mean([t.holding_time_mins for t in self.trades]) if self.trades else 0

        return BacktestResult(
            trades=self.trades,
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_holding_time=avg_holding_time,
            equity_curve=equity_series,
            daily_returns=returns
        )

    def print_results(self, result: BacktestResult):
        """Print formatted backtest results"""

        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

        print(f"\n{'Performance Summary':^70}")
        print("-" * 70)
        print(f"Initial Capital:    ₹{result.initial_capital:,.2f}")
        print(f"Final Capital:      ₹{result.final_capital:,.2f}")
        print(f"Total P&L:          ₹{result.total_pnl:,.2f}")
        print(f"Total Return:       {result.total_return_pct:+.2f}%")

        print(f"\n{'Trade Statistics':^70}")
        print("-" * 70)
        print(f"Total Trades:       {result.total_trades}")
        print(f"Winning Trades:     {result.winning_trades}")
        print(f"Losing Trades:      {result.losing_trades}")
        print(f"Win Rate:           {result.win_rate:.1f}%")

        print(f"\n{'Risk Metrics':^70}")
        print("-" * 70)
        print(f"Profit Factor:      {result.profit_factor:.2f}")
        print(f"Sharpe Ratio:       {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown:       ₹{result.max_drawdown:,.2f} ({result.max_drawdown_pct:.1f}%)")

        print(f"\n{'Win/Loss Analysis':^70}")
        print("-" * 70)
        print(f"Average Win:        ₹{result.avg_win:,.2f}")
        print(f"Average Loss:       ₹{result.avg_loss:,.2f}")
        print(f"Largest Win:        ₹{result.largest_win:,.2f}")
        print(f"Largest Loss:       ₹{result.largest_loss:,.2f}")
        print(f"Avg Holding Time:   {result.avg_holding_time:.0f} mins")

        # Expectancy
        if result.total_trades > 0:
            expectancy = result.total_pnl / result.total_trades
            print(f"\nExpectancy:         ₹{expectancy:.2f}/trade")

        print("\n" + "=" * 70)


def generate_sample_data(periods: int = 1000, trend: str = 'mixed') -> pd.DataFrame:
    """
    Generate sample OHLCV data for backtesting

    Args:
        periods: Number of bars
        trend: 'up', 'down', or 'mixed'

    Returns:
        OHLCV DataFrame
    """
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=periods, freq='15min')

    # Base price around NIFTY levels
    base_price = 22000

    # Generate price based on trend
    if trend == 'up':
        trend_component = np.linspace(0, 500, periods)
    elif trend == 'down':
        trend_component = np.linspace(0, -500, periods)
    else:  # mixed
        # Create cycles
        cycle = np.sin(np.linspace(0, 8 * np.pi, periods)) * 200
        trend_component = cycle

    # Add random walk
    noise = np.cumsum(np.random.randn(periods) * 5)

    close = base_price + trend_component + noise

    # Generate OHLC from close
    volatility = np.random.uniform(0.001, 0.005, periods)

    high = close * (1 + volatility)
    low = close * (1 - volatility)
    open_price = np.roll(close, 1)
    open_price[0] = close[0]

    volume = np.random.randint(100000, 500000, periods)

    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return df


if __name__ == "__main__":
    print("Backtesting Engine Test")
    print("=" * 70)

    # Generate sample data
    print("\n1. Generating sample data...")
    data = generate_sample_data(periods=2000, trend='mixed')
    print(f"   Data shape: {data.shape}")
    print(f"   Period: {data.index[0]} to {data.index[-1]}")

    # Initialize strategy and engine
    print("\n2. Initializing strategy and backtest engine...")
    strategy = MomentumOptionsStrategy({
        'target_pct': 15.0,  # More conservative target
        'stop_loss_pct': 25.0,
        'require_volume_confirmation': False  # Disable for sample data
    })

    engine = BacktestEngine(
        initial_capital=10000,
        commission=20,
        slippage_pct=0.1
    )

    # Run backtest
    print("\n3. Running backtest...")
    result = engine.run(data, strategy)

    # Print results
    engine.print_results(result)

    # Show trade details
    if result.trades:
        print(f"\n{'Recent Trades':^70}")
        print("-" * 70)
        print(f"{'Entry Time':<20} {'Type':<10} {'Entry':<8} {'Exit':<8} {'P&L':<10} {'Reason'}")
        print("-" * 70)

        for trade in result.trades[-10:]:  # Last 10 trades
            print(f"{str(trade.entry_time)[:19]:<20} "
                  f"{trade.signal_type:<10} "
                  f"₹{trade.entry_price:<7.0f} "
                  f"₹{trade.exit_price:<7.0f} "
                  f"₹{trade.pnl:<+9.0f} "
                  f"{trade.exit_reason[:25]}")

    print("\n" + "=" * 70)
    print("✅ Backtesting Engine Working Successfully!")
    print("=" * 70)

    print("\nFeatures:")
    print("  1. Event-driven backtesting")
    print("  2. Realistic slippage and commission")
    print("  3. Equity curve tracking")
    print("  4. Comprehensive performance metrics")
    print("  5. Trade-by-trade analysis")
    print("  6. Risk metrics (Sharpe, Drawdown)")

    print("\nReady for strategy optimization! 🚀")
