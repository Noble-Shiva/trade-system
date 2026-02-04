"""
Backtesting Engine - Simulate trading strategies on historical data
"""

from datetime import datetime, time as dtime
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from loguru import logger

from .data_loader import HistoricalDataLoader
from .metrics import PerformanceMetrics
from ..strategies import IronCondorStrategy, BullPutSpreadStrategy, BearCallSpreadStrategy
from ..risk import RiskManager, DynamicStopLoss
from ..data.option_chain import OptionChainAnalyzer


@dataclass
class BacktestTrade:
    """Record of a single trade"""
    trade_id: int
    date: datetime
    symbol: str
    strategy: str
    entry_price: float
    exit_price: float
    quantity: int
    side: str  # BUY or SELL
    pnl: float
    pnl_pct: float
    entry_reason: str
    exit_reason: str
    hold_time: int  # in minutes
    max_profit: float = 0
    max_loss: float = 0


@dataclass
class BacktestResult:
    """Results of a backtest run"""
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_hold_time: float
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    daily_returns: list = field(default_factory=list)


class BacktestEngine:
    """
    Backtesting engine to simulate trading strategies

    Features:
    - Event-driven simulation
    - Realistic order execution
    - Commission and slippage
    - Risk management
    - Detailed trade logging
    """

    def __init__(self, config: dict):
        self.config = config
        self.initial_capital = config.get("initial_capital", 100000)
        self.commission = config.get("commission", 20)  # per order
        self.slippage_pct = config.get("slippage_pct", 0.1)  # 0.1%

        # Initialize components
        self.data_loader = HistoricalDataLoader(config.get("data_path", "data/historical"))
        self.risk_manager = RiskManager(config.get("risk", {}))
        self.stop_loss_manager = DynamicStopLoss(config.get("stop_loss", {}))

        # State
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.trade_counter = 0

    def run(
        self,
        symbol: str,
        strategy_name: str,
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """
        Run backtest for a strategy

        Args:
            symbol: Index symbol (NIFTY, BANKNIFTY, etc.)
            strategy_name: Strategy to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            BacktestResult with all metrics
        """
        logger.info(f"Starting backtest: {strategy_name} on {symbol}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial capital: ₹{self.initial_capital:,.0f}")

        # Reset state
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = [(start_date, self.capital)]
        self.daily_returns = []
        self.trade_counter = 0

        # Load data
        try:
            index_data = self.data_loader.load_index_data(symbol)
            option_data = self.data_loader.load_option_data(symbol)
        except FileNotFoundError:
            logger.warning("Data not found. Downloading...")
            index_data = self.data_loader.download_index_data(symbol, start_date, end_date)
            option_data = self.data_loader.generate_synthetic_option_data(index_data, symbol)

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        index_data = index_data[(index_data['date'] >= start_dt) & (index_data['date'] <= end_dt)]

        # Initialize strategy
        strategy = self._get_strategy(strategy_name)

        # Simulate each day
        prev_capital = self.capital
        for idx, day_data in index_data.iterrows():
            current_date = day_data['date']
            spot_price = day_data['close']

            # Get option data for this day
            day_options = option_data[option_data['date'] == current_date]

            if day_options.empty:
                continue

            # Build option chain
            chain_data = self._build_chain_from_data(day_options)

            market_data = {
                "symbol": symbol,
                "spot_price": spot_price,
                "option_chain": chain_data,
                "vix": 15,  # Assume moderate VIX
                "date": current_date
            }

            # Check exit conditions for existing positions
            self._check_exits(market_data)

            # Check for new entries
            can_trade, reason = self.risk_manager.can_trade(self.capital)
            if can_trade and not self.positions:
                signals = strategy.analyze(market_data)
                for signal in signals:
                    self._execute_signal(signal, market_data)

            # Record daily equity
            self.equity_curve.append((current_date.strftime("%Y-%m-%d"), self.capital))

            # Calculate daily return
            daily_return = (self.capital - prev_capital) / prev_capital if prev_capital > 0 else 0
            self.daily_returns.append(daily_return)
            prev_capital = self.capital

        # Close any remaining positions
        if self.positions:
            last_date = index_data.iloc[-1]['date']
            last_price = index_data.iloc[-1]['close']
            for pos in self.positions[:]:
                self._close_position(pos, last_price, "End of backtest", last_date)

        # Calculate metrics
        result = self._calculate_results(start_date, end_date)

        logger.info(f"Backtest complete: {result.total_trades} trades")
        logger.info(f"Final capital: ₹{result.final_capital:,.0f}")
        logger.info(f"Total return: {result.total_return_pct:.2f}%")
        logger.info(f"Win rate: {result.win_rate:.1f}%")
        logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")

        return result

    def _get_strategy(self, name: str):
        """Get strategy instance by name"""
        strategy_config = self.config.get("strategies", {}).get(name, {})

        strategies = {
            "iron_condor": IronCondorStrategy,
            "bull_put_spread": BullPutSpreadStrategy,
            "bear_call_spread": BearCallSpreadStrategy
        }

        if name not in strategies:
            raise ValueError(f"Unknown strategy: {name}")

        return strategies[name](strategy_config)

    def _build_chain_from_data(self, day_options: pd.DataFrame) -> list:
        """Build option chain format from DataFrame"""
        chain = []
        for _, row in day_options.iterrows():
            chain.append({
                "strikePrice": row['strike'],
                "CE": {
                    "lastPrice": row['call_price'],
                    "openInterest": row['call_oi'],
                    "impliedVolatility": row.get('iv', 15)
                },
                "PE": {
                    "lastPrice": row['put_price'],
                    "openInterest": row['put_oi'],
                    "impliedVolatility": row.get('iv', 15)
                }
            })
        return chain

    def _execute_signal(self, signal, market_data: dict):
        """Execute a trading signal"""
        # Apply slippage
        if signal.action == "BUY":
            exec_price = signal.price * (1 + self.slippage_pct / 100)
        else:
            exec_price = signal.price * (1 - self.slippage_pct / 100)

        # Deduct commission
        self.capital -= self.commission

        # Create position
        position = {
            "trade_id": self.trade_counter,
            "symbol": signal.symbol,
            "entry_price": exec_price,
            "quantity": signal.quantity,
            "side": signal.action,
            "stop_loss": signal.stop_loss,
            "target": signal.target,
            "strategy": signal.metadata.get("strategy", ""),
            "entry_date": market_data["date"],
            "entry_reason": signal.reason,
            "max_profit": 0,
            "max_loss": 0
        }
        self.positions.append(position)
        self.risk_manager.add_position()
        self.trade_counter += 1

    def _check_exits(self, market_data: dict):
        """Check if any positions should be exited"""
        spot_price = market_data["spot_price"]

        for pos in self.positions[:]:
            # Estimate current option price based on spot movement
            # This is simplified - real implementation would use the option chain
            entry = pos["entry_price"]
            pct_change = (spot_price - market_data.get("prev_spot", spot_price)) / spot_price

            if pos["side"] == "SELL":
                # For sold options, price decreases = profit
                current_price = entry * (1 - pct_change * 0.5)  # Delta ~ 0.5
            else:
                current_price = entry * (1 + pct_change * 0.5)

            current_price = max(0.5, current_price)  # Minimum price

            # Track max profit/loss
            if pos["side"] == "SELL":
                pnl = entry - current_price
            else:
                pnl = current_price - entry

            if pnl > pos["max_profit"]:
                pos["max_profit"] = pnl
            if pnl < pos["max_loss"]:
                pos["max_loss"] = pnl

            # Check stop loss
            if pos["side"] == "SELL" and current_price >= pos["stop_loss"]:
                self._close_position(pos, current_price, "Stop loss hit", market_data["date"])
                continue

            # Check target (50% of premium for sold options)
            if pos["side"] == "SELL" and pos["target"] > 0:
                if current_price <= pos["target"]:
                    self._close_position(pos, current_price, "Target reached", market_data["date"])
                    continue

    def _close_position(self, position: dict, exit_price: float, reason: str, date):
        """Close a position and record the trade"""
        # Apply slippage
        if position["side"] == "SELL":
            exec_price = exit_price * (1 + self.slippage_pct / 100)  # Buy back
        else:
            exec_price = exit_price * (1 - self.slippage_pct / 100)  # Sell

        # Calculate P&L
        if position["side"] == "SELL":
            pnl = (position["entry_price"] - exec_price) * position["quantity"]
        else:
            pnl = (exec_price - position["entry_price"]) * position["quantity"]

        # Deduct commission
        pnl -= self.commission

        # Update capital
        self.capital += pnl

        # Calculate hold time
        entry_date = position["entry_date"]
        if isinstance(entry_date, str):
            entry_date = pd.to_datetime(entry_date)
        if isinstance(date, str):
            date = pd.to_datetime(date)
        hold_time = (date - entry_date).days * 390  # Trading minutes per day

        # Record trade
        pnl_pct = (pnl / (position["entry_price"] * position["quantity"])) * 100

        trade = BacktestTrade(
            trade_id=position["trade_id"],
            date=entry_date,
            symbol=position["symbol"],
            strategy=position["strategy"],
            entry_price=position["entry_price"],
            exit_price=exec_price,
            quantity=position["quantity"],
            side=position["side"],
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_reason=position["entry_reason"],
            exit_reason=reason,
            hold_time=hold_time,
            max_profit=position["max_profit"],
            max_loss=position["max_loss"]
        )
        self.trades.append(trade)

        # Update risk manager
        self.risk_manager.update_pnl(pnl, self.capital)
        self.risk_manager.remove_position()

        # Remove position
        self.positions.remove(position)

        logger.debug(f"Closed {position['symbol']}: P&L ₹{pnl:.2f} ({reason})")

    def _calculate_results(self, start_date: str, end_date: str) -> BacktestResult:
        """Calculate backtest performance metrics"""
        metrics = PerformanceMetrics(self.trades, self.initial_capital, self.daily_returns)

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_return=self.capital - self.initial_capital,
            total_return_pct=((self.capital - self.initial_capital) / self.initial_capital) * 100,
            total_trades=len(self.trades),
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            max_drawdown=metrics.max_drawdown,
            max_drawdown_pct=metrics.max_drawdown_pct,
            avg_win=metrics.avg_win,
            avg_loss=metrics.avg_loss,
            largest_win=metrics.largest_win,
            largest_loss=metrics.largest_loss,
            avg_hold_time=metrics.avg_hold_time,
            trades=self.trades,
            equity_curve=self.equity_curve,
            daily_returns=self.daily_returns
        )
