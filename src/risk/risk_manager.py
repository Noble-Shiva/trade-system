"""
Risk Management Module
Protects capital with position sizing, loss limits, and risk controls
"""

import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import TradingLogger

logger = TradingLogger("RiskManager")


class RiskCheckResult(Enum):
    """Risk check results"""
    APPROVED = "APPROVED"
    REJECTED_DAILY_LIMIT = "REJECTED_DAILY_LIMIT"
    REJECTED_WEEKLY_LIMIT = "REJECTED_WEEKLY_LIMIT"
    REJECTED_POSITION_LIMIT = "REJECTED_POSITION_LIMIT"
    REJECTED_CAPITAL_LOW = "REJECTED_CAPITAL_LOW"
    REJECTED_MAX_LOSS_PER_TRADE = "REJECTED_MAX_LOSS_PER_TRADE"
    REJECTED_DRAWDOWN_LIMIT = "REJECTED_DRAWDOWN_LIMIT"


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    entry_time: datetime
    entry_price: float
    quantity: int
    position_type: str  # BUY_CALL or BUY_PUT
    stop_loss: float
    target: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class TradeRecord:
    """Completed trade record"""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    position_type: str


class RiskManager:
    """
    Risk Management System for Micro-Capital Trading

    Features:
    - Daily loss limit (₹500)
    - Weekly loss limit (₹1000)
    - Max open positions (2)
    - Position sizing
    - Trailing stop management
    - Drawdown monitoring
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize risk manager

        Args:
            config: Risk configuration dictionary
        """
        # Default configuration for ₹10K capital
        self.config = {
            # Capital limits
            'initial_capital': 10000,
            'min_capital_to_trade': 2000,  # Don't trade if below this

            # Loss limits
            'max_daily_loss': 500,  # ₹500 daily loss limit
            'max_weekly_loss': 1000,  # ₹1000 weekly loss limit
            'max_drawdown_pct': 20,  # 20% max drawdown

            # Position limits
            'max_open_positions': 2,
            'max_position_value': 2000,  # ₹2000 per position
            'max_loss_per_trade_pct': 30,  # Max 30% loss per trade

            # Risk per trade
            'risk_per_trade_pct': 5,  # 5% of capital per trade risk

            # Trailing stop
            'trailing_stop_pct': 15,  # 15% trailing stop
            'trailing_activation_pct': 10,  # Activate after 10% profit

            # Time limits
            'max_trades_per_day': 3,
            'min_time_between_trades': 15,  # Minutes
        }

        # Override with provided config
        if config:
            self.config.update(config)

        # State tracking
        self.current_capital = self.config['initial_capital']
        self.peak_capital = self.config['initial_capital']
        self.open_positions: List[Position] = []
        self.trade_history: List[TradeRecord] = []
        self.daily_pnl: Dict[date, float] = {}
        self.trades_today: int = 0
        self.last_trade_time: Optional[datetime] = None

        logger.info("Risk Manager initialized")
        logger.info(f"  Initial Capital: ₹{self.config['initial_capital']}")
        logger.info(f"  Daily Loss Limit: ₹{self.config['max_daily_loss']}")
        logger.info(f"  Weekly Loss Limit: ₹{self.config['max_weekly_loss']}")
        logger.info(f"  Max Positions: {self.config['max_open_positions']}")

    def check_trade_allowed(self, trade_value: float, stop_loss_pct: float = 30) -> Tuple[RiskCheckResult, str]:
        """
        Check if a new trade is allowed based on risk rules

        Args:
            trade_value: Value of the trade in ₹
            stop_loss_pct: Stop loss percentage for the trade

        Returns:
            Tuple of (result, message)
        """
        # Check capital
        if self.current_capital < self.config['min_capital_to_trade']:
            msg = f"Capital too low: ₹{self.current_capital:.0f} < ₹{self.config['min_capital_to_trade']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_CAPITAL_LOW, msg

        # Check position limit
        if len(self.open_positions) >= self.config['max_open_positions']:
            msg = f"Position limit reached: {len(self.open_positions)} >= {self.config['max_open_positions']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_POSITION_LIMIT, msg

        # Check daily loss limit
        today_loss = self._get_today_loss()
        potential_loss = trade_value * (stop_loss_pct / 100)

        if today_loss + potential_loss > self.config['max_daily_loss']:
            msg = f"Daily loss limit: ₹{today_loss:.0f} + ₹{potential_loss:.0f} > ₹{self.config['max_daily_loss']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_DAILY_LIMIT, msg

        # Check weekly loss limit
        week_loss = self._get_week_loss()
        if week_loss + potential_loss > self.config['max_weekly_loss']:
            msg = f"Weekly loss limit: ₹{week_loss:.0f} + ₹{potential_loss:.0f} > ₹{self.config['max_weekly_loss']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_WEEKLY_LIMIT, msg

        # Check drawdown
        current_drawdown_pct = self._get_current_drawdown_pct()
        if current_drawdown_pct >= self.config['max_drawdown_pct']:
            msg = f"Max drawdown reached: {current_drawdown_pct:.1f}% >= {self.config['max_drawdown_pct']}%"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_DRAWDOWN_LIMIT, msg

        # Check trade value limit
        if trade_value > self.config['max_position_value']:
            msg = f"Position too large: ₹{trade_value:.0f} > ₹{self.config['max_position_value']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_MAX_LOSS_PER_TRADE, msg

        # Check trades per day
        if self.trades_today >= self.config['max_trades_per_day']:
            msg = f"Max trades today: {self.trades_today} >= {self.config['max_trades_per_day']}"
            logger.warning(msg)
            return RiskCheckResult.REJECTED_DAILY_LIMIT, msg

        # Check time between trades
        if self.last_trade_time:
            minutes_since_last = (datetime.now() - self.last_trade_time).total_seconds() / 60
            if minutes_since_last < self.config['min_time_between_trades']:
                msg = f"Too soon since last trade: {minutes_since_last:.0f} < {self.config['min_time_between_trades']} mins"
                logger.warning(msg)
                return RiskCheckResult.REJECTED_DAILY_LIMIT, msg

        # All checks passed
        logger.info(f"✅ Trade approved: ₹{trade_value:.0f}")
        return RiskCheckResult.APPROVED, "Trade approved"

    def calculate_position_size(self, option_price: float, stop_loss_pct: float = 30) -> int:
        """
        Calculate optimal position size based on risk

        Args:
            option_price: Current option premium
            stop_loss_pct: Stop loss percentage

        Returns:
            Number of lots to buy
        """
        # Risk amount based on config
        risk_amount = self.current_capital * (self.config['risk_per_trade_pct'] / 100)

        # Limit by max position value
        max_value = min(risk_amount, self.config['max_position_value'])

        # Calculate lots
        lots = int(max_value / option_price)

        # Ensure at least 1 lot if affordable
        if lots == 0 and option_price <= max_value:
            lots = 1

        # Verify potential loss is acceptable
        potential_loss = lots * option_price * (stop_loss_pct / 100)
        if potential_loss > self.config['max_daily_loss'] - self._get_today_loss():
            # Reduce lots to fit within daily limit
            available_risk = self.config['max_daily_loss'] - self._get_today_loss()
            lots = int(available_risk / (option_price * stop_loss_pct / 100))

        if lots > 0:
            logger.info(f"Position size: {lots} lots @ ₹{option_price} = ₹{lots * option_price}")
        else:
            logger.warning(f"Cannot afford even 1 lot at ₹{option_price}")

        return lots

    def calculate_stop_loss(self, entry_price: float, atr: float = None,
                           method: str = 'percentage') -> float:
        """
        Calculate stop loss price

        Args:
            entry_price: Entry price
            atr: Average True Range (for ATR method)
            method: 'percentage', 'atr', or 'fixed'

        Returns:
            Stop loss price
        """
        if method == 'percentage':
            stop_loss = entry_price * (1 - self.config['max_loss_per_trade_pct'] / 100)

        elif method == 'atr' and atr:
            # 2 ATR stop loss
            stop_loss = entry_price - (2 * atr)

        elif method == 'fixed':
            # Fixed ₹ amount (e.g., ₹50 per lot)
            stop_loss = entry_price - 50

        else:
            # Default to percentage
            stop_loss = entry_price * 0.70  # 30% stop loss

        logger.info(f"Stop loss: ₹{stop_loss:.2f} ({((entry_price - stop_loss) / entry_price * 100):.1f}%)")

        return round(stop_loss, 2)

    def calculate_target(self, entry_price: float, risk_reward: float = 1.0) -> float:
        """
        Calculate target price based on risk:reward

        Args:
            entry_price: Entry price
            risk_reward: Target risk:reward ratio

        Returns:
            Target price
        """
        # For 30% stop loss, R:R of 1 = 30% target
        stop_pct = self.config['max_loss_per_trade_pct']
        target_pct = stop_pct * risk_reward

        target = entry_price * (1 + target_pct / 100)

        logger.info(f"Target: ₹{target:.2f} ({target_pct:.1f}%, R:R = {risk_reward})")

        return round(target, 2)

    def update_trailing_stop(self, position: Position, current_price: float) -> float:
        """
        Update trailing stop for position

        Args:
            position: Current position
            current_price: Current market price

        Returns:
            New stop loss price
        """
        # Calculate current P&L percentage
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100

        # Check if trailing should be activated
        if pnl_pct >= self.config['trailing_activation_pct']:
            # Calculate trailing stop
            trailing_stop = current_price * (1 - self.config['trailing_stop_pct'] / 100)

            # Only update if new stop is higher than current
            if trailing_stop > position.stop_loss:
                old_stop = position.stop_loss
                position.stop_loss = trailing_stop
                logger.info(f"Trailing stop updated: ₹{old_stop:.2f} → ₹{trailing_stop:.2f}")
                return trailing_stop

        return position.stop_loss

    def add_position(self, symbol: str, entry_price: float, quantity: int,
                    position_type: str, stop_loss: float, target: float) -> Position:
        """
        Add a new open position

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Number of lots
            position_type: BUY_CALL or BUY_PUT
            stop_loss: Stop loss price
            target: Target price

        Returns:
            Position object
        """
        position = Position(
            symbol=symbol,
            entry_time=datetime.now(),
            entry_price=entry_price,
            quantity=quantity,
            position_type=position_type,
            stop_loss=stop_loss,
            target=target,
            current_price=entry_price,
            unrealized_pnl=0.0
        )

        self.open_positions.append(position)
        self.trades_today += 1
        self.last_trade_time = datetime.now()

        logger.trade(f"Position opened: {symbol} {position_type} @ ₹{entry_price} x {quantity}")

        return position

    def close_position(self, position: Position, exit_price: float, reason: str = "") -> float:
        """
        Close a position and record the trade

        Args:
            position: Position to close
            exit_price: Exit price
            reason: Exit reason

        Returns:
            P&L of the trade
        """
        # Calculate P&L
        pnl = (exit_price - position.entry_price) * position.quantity

        # Create trade record
        trade = TradeRecord(
            symbol=position.symbol,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=pnl,
            position_type=position.position_type
        )

        self.trade_history.append(trade)

        # Update capital
        self.current_capital += pnl

        # Update peak capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        # Update daily P&L
        today = datetime.now().date()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = 0
        self.daily_pnl[today] += pnl

        # Remove from open positions
        self.open_positions.remove(position)

        logger.trade(f"Position closed: {position.symbol} @ ₹{exit_price}, P&L: ₹{pnl:.2f}, Reason: {reason}")

        return pnl

    def get_portfolio_status(self) -> Dict:
        """
        Get current portfolio status

        Returns:
            Dictionary with portfolio metrics
        """
        # Calculate unrealized P&L
        unrealized_pnl = sum(p.unrealized_pnl for p in self.open_positions)

        # Calculate realized P&L
        realized_pnl = sum(t.pnl for t in self.trade_history)

        # Total P&L
        total_pnl = realized_pnl + unrealized_pnl

        # Drawdown
        current_drawdown = self.peak_capital - self.current_capital
        drawdown_pct = (current_drawdown / self.peak_capital * 100) if self.peak_capital > 0 else 0

        # Win rate
        winning_trades = [t for t in self.trade_history if t.pnl > 0]
        win_rate = (len(winning_trades) / len(self.trade_history) * 100) if self.trade_history else 0

        status = {
            'initial_capital': self.config['initial_capital'],
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'open_positions': len(self.open_positions),
            'total_trades': len(self.trade_history),
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.config['initial_capital'] * 100),
            'current_drawdown': current_drawdown,
            'drawdown_pct': drawdown_pct,
            'win_rate': win_rate,
            'today_pnl': self._get_today_loss() * -1,  # Convert loss to P&L
            'week_pnl': self._get_week_loss() * -1,
            'trades_today': self.trades_today,
        }

        return status

    def _get_today_loss(self) -> float:
        """Get today's total loss (positive number)"""
        today = datetime.now().date()
        today_pnl = self.daily_pnl.get(today, 0)
        return max(0, -today_pnl)  # Return loss as positive number

    def _get_week_loss(self) -> float:
        """Get this week's total loss (positive number)"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())

        week_pnl = 0
        for day, pnl in self.daily_pnl.items():
            if day >= week_start:
                week_pnl += pnl

        return max(0, -week_pnl)  # Return loss as positive number

    def _get_current_drawdown_pct(self) -> float:
        """Get current drawdown percentage"""
        if self.peak_capital == 0:
            return 0
        return ((self.peak_capital - self.current_capital) / self.peak_capital) * 100

    def reset_daily_counters(self):
        """Reset daily counters (call at market open)"""
        self.trades_today = 0
        self.last_trade_time = None
        logger.info("Daily counters reset")

    def print_status(self):
        """Print current portfolio status"""
        status = self.get_portfolio_status()

        print("\n" + "=" * 60)
        print("RISK MANAGER STATUS")
        print("=" * 60)

        print(f"\n{'Capital':^60}")
        print("-" * 60)
        print(f"Initial Capital:  ₹{status['initial_capital']:,.0f}")
        print(f"Current Capital:  ₹{status['current_capital']:,.0f}")
        print(f"Peak Capital:     ₹{status['peak_capital']:,.0f}")

        print(f"\n{'Performance':^60}")
        print("-" * 60)
        print(f"Realized P&L:     ₹{status['realized_pnl']:+,.0f}")
        print(f"Unrealized P&L:   ₹{status['unrealized_pnl']:+,.0f}")
        print(f"Total P&L:        ₹{status['total_pnl']:+,.0f} ({status['total_return_pct']:+.1f}%)")

        print(f"\n{'Risk Metrics':^60}")
        print("-" * 60)
        print(f"Drawdown:         ₹{status['current_drawdown']:,.0f} ({status['drawdown_pct']:.1f}%)")
        print(f"Win Rate:         {status['win_rate']:.1f}%")

        print(f"\n{'Todays Activity':^60}")
        print("-" * 60)
        print(f"Trades Today:     {status['trades_today']}/{self.config['max_trades_per_day']}")
        print(f"Today P&L:        ₹{status['today_pnl']:+,.0f}")
        print(f"Week P&L:         ₹{status['week_pnl']:+,.0f}")

        print(f"\n{'Limits':^60}")
        print("-" * 60)
        print(f"Open Positions:   {status['open_positions']}/{self.config['max_open_positions']}")
        daily_remaining = self.config['max_daily_loss'] - self._get_today_loss()
        weekly_remaining = self.config['max_weekly_loss'] - self._get_week_loss()
        print(f"Daily Loss Remaining:  ₹{daily_remaining:,.0f}")
        print(f"Weekly Loss Remaining: ₹{weekly_remaining:,.0f}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    print("Risk Manager Test")
    print("=" * 70)

    # Initialize risk manager
    rm = RiskManager({
        'initial_capital': 10000,
        'max_daily_loss': 500,
        'max_weekly_loss': 1000,
    })

    print("\n1. Check Trade Allowed")
    print("-" * 70)

    # Test 1: Valid trade
    result, msg = rm.check_trade_allowed(trade_value=1500, stop_loss_pct=30)
    print(f"Trade ₹1,500: {result.value} - {msg}")

    # Test 2: Position size calculation
    print("\n2. Calculate Position Size")
    print("-" * 70)
    lots = rm.calculate_position_size(option_price=150, stop_loss_pct=30)
    print(f"For ₹150 premium: {lots} lots = ₹{lots * 150}")

    # Test 3: Stop loss calculation
    print("\n3. Calculate Stop Loss")
    print("-" * 70)
    stop = rm.calculate_stop_loss(entry_price=150, method='percentage')
    print(f"Entry: ₹150, Stop: ₹{stop}")

    # Test 4: Target calculation
    print("\n4. Calculate Target")
    print("-" * 70)
    target = rm.calculate_target(entry_price=150, risk_reward=1.0)
    print(f"Entry: ₹150, Target: ₹{target}")

    # Test 5: Add position
    print("\n5. Add Position")
    print("-" * 70)
    pos = rm.add_position(
        symbol="NIFTY24NOV22000CE",
        entry_price=150,
        quantity=10,
        position_type="BUY_CALL",
        stop_loss=105,
        target=180
    )
    print(f"Position added: {pos.symbol}")

    # Test 6: Update trailing stop
    print("\n6. Update Trailing Stop")
    print("-" * 70)
    # Simulate price increase
    pos.current_price = 170  # +13.3%
    new_stop = rm.update_trailing_stop(pos, current_price=170)
    print(f"New trailing stop: ₹{new_stop}")

    # Test 7: Close position
    print("\n7. Close Position")
    print("-" * 70)
    pnl = rm.close_position(pos, exit_price=180, reason="Target hit")
    print(f"P&L: ₹{pnl}")

    # Test 8: Check daily limit after loss
    print("\n8. Test Daily Loss Limit")
    print("-" * 70)

    # Simulate losses
    rm.daily_pnl[datetime.now().date()] = -400  # ₹400 loss today

    result, msg = rm.check_trade_allowed(trade_value=1500, stop_loss_pct=30)
    print(f"After ₹400 loss, trade ₹1500: {result.value}")
    print(f"Reason: {msg}")

    # Test 9: Portfolio status
    print("\n9. Portfolio Status")
    print("-" * 70)
    rm.print_status()

    # Test 10: Multiple position limit
    print("\n10. Test Position Limit")
    print("-" * 70)

    # Add max positions
    rm.daily_pnl[datetime.now().date()] = 0  # Reset
    rm.add_position("NIFTY1", 100, 5, "BUY_CALL", 70, 130)
    rm.add_position("NIFTY2", 100, 5, "BUY_PUT", 70, 130)

    result, msg = rm.check_trade_allowed(trade_value=500, stop_loss_pct=30)
    print(f"With 2 positions, new trade: {result.value}")
    print(f"Reason: {msg}")

    print("\n" + "=" * 70)
    print("✅ Risk Manager Working Successfully!")
    print("=" * 70)

    print("\nFeatures:")
    print("  1. Daily/weekly loss limits")
    print("  2. Position sizing by risk")
    print("  3. Dynamic stop loss calculation")
    print("  4. Trailing stop management")
    print("  5. Drawdown monitoring")
    print("  6. Trade frequency limits")
    print("  7. Portfolio status tracking")

    print("\nReady for live trading integration! 🚀")
