"""
Performance Metrics Calculator
"""

import numpy as np
from typing import List
from loguru import logger


class PerformanceMetrics:
    """
    Calculate trading performance metrics

    Metrics include:
    - Win rate
    - Profit factor
    - Sharpe ratio
    - Sortino ratio
    - Maximum drawdown
    - Average win/loss
    - Expectancy
    """

    def __init__(self, trades: list, initial_capital: float, daily_returns: list):
        self.trades = trades
        self.initial_capital = initial_capital
        self.daily_returns = daily_returns

        # Calculate all metrics
        self._calculate_metrics()

    def _calculate_metrics(self):
        """Calculate all performance metrics"""
        if not self.trades:
            self._set_default_metrics()
            return

        # Basic stats
        pnls = [t.pnl for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        self.total_trades = len(self.trades)

        # Win rate
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # Average win/loss
        self.avg_win = np.mean(wins) if wins else 0
        self.avg_loss = np.mean(losses) if losses else 0
        self.largest_win = max(wins) if wins else 0
        self.largest_loss = min(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Expectancy
        self.expectancy = np.mean(pnls) if pnls else 0

        # Average hold time
        hold_times = [t.hold_time for t in self.trades]
        self.avg_hold_time = np.mean(hold_times) if hold_times else 0

        # Risk-adjusted returns
        self._calculate_risk_metrics()

        # Drawdown
        self._calculate_drawdown()

    def _calculate_risk_metrics(self):
        """Calculate Sharpe and Sortino ratios"""
        if not self.daily_returns or len(self.daily_returns) < 2:
            self.sharpe_ratio = 0
            self.sortino_ratio = 0
            return

        returns = np.array(self.daily_returns)

        # Annualized metrics (252 trading days)
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Sharpe Ratio (assuming risk-free rate = 6% annual = 0.024% daily)
        risk_free_daily = 0.06 / 252
        if std_return > 0:
            self.sharpe_ratio = np.sqrt(252) * (mean_return - risk_free_daily) / std_return
        else:
            self.sharpe_ratio = 0

        # Sortino Ratio (only downside deviation)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_std = np.std(negative_returns)
            if downside_std > 0:
                self.sortino_ratio = np.sqrt(252) * (mean_return - risk_free_daily) / downside_std
            else:
                self.sortino_ratio = 0
        else:
            self.sortino_ratio = float('inf')  # No negative returns

    def _calculate_drawdown(self):
        """Calculate maximum drawdown"""
        if not self.trades:
            self.max_drawdown = 0
            self.max_drawdown_pct = 0
            return

        # Build equity curve from trades
        equity = [self.initial_capital]
        for trade in self.trades:
            equity.append(equity[-1] + trade.pnl)

        equity = np.array(equity)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity

        self.max_drawdown = np.max(drawdown)
        self.max_drawdown_pct = (self.max_drawdown / np.max(peak)) * 100 if np.max(peak) > 0 else 0

    def _set_default_metrics(self):
        """Set default values when no trades"""
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_trades = 0
        self.win_rate = 0
        self.avg_win = 0
        self.avg_loss = 0
        self.largest_win = 0
        self.largest_loss = 0
        self.profit_factor = 0
        self.expectancy = 0
        self.avg_hold_time = 0
        self.sharpe_ratio = 0
        self.sortino_ratio = 0
        self.max_drawdown = 0
        self.max_drawdown_pct = 0

    def get_summary(self) -> dict:
        """Get summary of all metrics"""
        return {
            "Total Trades": self.total_trades,
            "Winning Trades": self.winning_trades,
            "Losing Trades": self.losing_trades,
            "Win Rate": f"{self.win_rate:.1f}%",
            "Profit Factor": f"{self.profit_factor:.2f}",
            "Sharpe Ratio": f"{self.sharpe_ratio:.2f}",
            "Sortino Ratio": f"{self.sortino_ratio:.2f}",
            "Max Drawdown": f"₹{self.max_drawdown:.0f} ({self.max_drawdown_pct:.1f}%)",
            "Average Win": f"₹{self.avg_win:.0f}",
            "Average Loss": f"₹{self.avg_loss:.0f}",
            "Largest Win": f"₹{self.largest_win:.0f}",
            "Largest Loss": f"₹{self.largest_loss:.0f}",
            "Expectancy": f"₹{self.expectancy:.0f}",
            "Avg Hold Time": f"{self.avg_hold_time:.0f} mins"
        }

    def print_summary(self):
        """Print formatted summary"""
        print("\n" + "=" * 50)
        print("PERFORMANCE METRICS")
        print("=" * 50)

        for key, value in self.get_summary().items():
            print(f"{key:20}: {value}")

        print("=" * 50)

    def is_profitable(self) -> bool:
        """Check if strategy is profitable"""
        return self.profit_factor > 1.0

    def meets_criteria(
        self,
        min_win_rate: float = 50,
        min_profit_factor: float = 1.5,
        min_sharpe: float = 1.0,
        max_drawdown_pct: float = 20
    ) -> tuple[bool, list[str]]:
        """
        Check if metrics meet minimum criteria

        Returns:
            (passes, list of failed criteria)
        """
        failures = []

        if self.win_rate < min_win_rate:
            failures.append(f"Win rate {self.win_rate:.1f}% < {min_win_rate}%")

        if self.profit_factor < min_profit_factor:
            failures.append(f"Profit factor {self.profit_factor:.2f} < {min_profit_factor}")

        if self.sharpe_ratio < min_sharpe:
            failures.append(f"Sharpe ratio {self.sharpe_ratio:.2f} < {min_sharpe}")

        if self.max_drawdown_pct > max_drawdown_pct:
            failures.append(f"Max drawdown {self.max_drawdown_pct:.1f}% > {max_drawdown_pct}%")

        return len(failures) == 0, failures


def calculate_cagr(initial: float, final: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate"""
    if initial <= 0 or years <= 0:
        return 0
    return (pow(final / initial, 1 / years) - 1) * 100


def calculate_calmar_ratio(cagr: float, max_drawdown_pct: float) -> float:
    """Calculate Calmar Ratio (CAGR / Max Drawdown)"""
    if max_drawdown_pct <= 0:
        return float('inf')
    return cagr / max_drawdown_pct
