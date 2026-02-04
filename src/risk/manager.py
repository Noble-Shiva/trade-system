"""
Risk Manager - Control overall trading risk
"""

from datetime import datetime, date
from loguru import logger


class RiskManager:
    """
    Manages overall portfolio risk including:
    - Daily loss limits
    - Position sizing
    - Max open positions
    - Drawdown protection
    """

    def __init__(self, config: dict):
        self.max_capital_per_trade_pct = config.get("max_capital_per_trade_pct", 5.0)
        self.max_daily_loss_pct = config.get("max_daily_loss_pct", 2.0)
        self.max_weekly_loss_pct = config.get("max_weekly_loss_pct", 5.0)
        self.max_drawdown_pct = config.get("max_drawdown_pct", 10.0)
        self.max_open_positions = config.get("max_open_positions", 3)

        # Track daily P&L
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.peak_capital = 0.0
        self.current_date = date.today()
        self.open_positions = 0

        # Emergency flags
        self.trading_paused = False
        self.pause_reason = ""

    def can_trade(self, capital: float) -> tuple[bool, str]:
        """
        Check if new trades are allowed

        Returns:
            (can_trade, reason)
        """
        if self.trading_paused:
            return False, f"Trading paused: {self.pause_reason}"

        # Check daily loss limit
        max_daily_loss = capital * (self.max_daily_loss_pct / 100)
        if self.daily_pnl <= -max_daily_loss:
            return False, f"Daily loss limit hit: ₹{abs(self.daily_pnl):.0f}"

        # Check weekly loss limit
        max_weekly_loss = capital * (self.max_weekly_loss_pct / 100)
        if self.weekly_pnl <= -max_weekly_loss:
            return False, f"Weekly loss limit hit: ₹{abs(self.weekly_pnl):.0f}"

        # Check drawdown
        if self.peak_capital > 0:
            drawdown = ((self.peak_capital - capital) / self.peak_capital) * 100
            if drawdown >= self.max_drawdown_pct:
                return False, f"Max drawdown hit: {drawdown:.1f}%"

        # Check max positions
        if self.open_positions >= self.max_open_positions:
            return False, f"Max positions reached: {self.open_positions}"

        return True, "OK"

    def calculate_position_size(
        self,
        capital: float,
        risk_per_lot: float,
        min_lots: int = 1
    ) -> int:
        """
        Calculate position size based on risk

        Args:
            capital: Available capital
            risk_per_lot: Max loss per lot
            min_lots: Minimum lots to trade

        Returns:
            Number of lots
        """
        max_risk = capital * (self.max_capital_per_trade_pct / 100)
        lots = int(max_risk / risk_per_lot) if risk_per_lot > 0 else min_lots

        return max(min_lots, lots)

    def update_pnl(self, pnl: float, capital: float):
        """Update daily/weekly P&L and peak capital"""
        # Reset daily P&L if new day
        today = date.today()
        if today != self.current_date:
            self.daily_pnl = 0.0
            self.current_date = today

            # Reset weekly P&L on Monday
            if today.weekday() == 0:
                self.weekly_pnl = 0.0

        self.daily_pnl += pnl
        self.weekly_pnl += pnl

        # Update peak capital
        if capital > self.peak_capital:
            self.peak_capital = capital

        logger.info(f"P&L Updated - Daily: ₹{self.daily_pnl:.0f}, Weekly: ₹{self.weekly_pnl:.0f}")

    def add_position(self):
        """Track new position opened"""
        self.open_positions += 1

    def remove_position(self):
        """Track position closed"""
        self.open_positions = max(0, self.open_positions - 1)

    def pause_trading(self, reason: str):
        """Pause all trading"""
        self.trading_paused = True
        self.pause_reason = reason
        logger.warning(f"Trading paused: {reason}")

    def resume_trading(self):
        """Resume trading"""
        self.trading_paused = False
        self.pause_reason = ""
        logger.info("Trading resumed")

    def get_status(self) -> dict:
        """Get current risk status"""
        return {
            "trading_paused": self.trading_paused,
            "pause_reason": self.pause_reason,
            "daily_pnl": self.daily_pnl,
            "weekly_pnl": self.weekly_pnl,
            "open_positions": self.open_positions,
            "max_positions": self.max_open_positions
        }

    def check_circuit_breaker(self, consecutive_losses: int) -> bool:
        """
        Check if circuit breaker should trigger

        Returns True if trading should be paused
        """
        if consecutive_losses >= 3:
            self.pause_trading(f"Circuit breaker: {consecutive_losses} consecutive losses")
            return True
        return False
