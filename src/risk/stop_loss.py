"""
Dynamic Stop Loss Manager
"""

from datetime import datetime, time
from dataclasses import dataclass
from loguru import logger


@dataclass
class StopLossLevel:
    price: float
    reason: str
    timestamp: datetime


class DynamicStopLoss:
    """
    Dynamic stop-loss that adjusts based on:
    - Profit levels (trailing)
    - Time of day
    - Volatility (ATR)
    """

    def __init__(self, config: dict):
        self.initial_sl_pct = config.get("initial_sl_pct", 2.0)
        self.trailing_start_pct = config.get("trailing_start_pct", 1.5)
        self.trail_pct = config.get("trail_pct", 0.5)

        # Time-based multipliers
        self.time_multipliers = config.get("time_based", {
            "morning_multiplier": 0.8,   # Tighter in morning (volatile)
            "midday_multiplier": 1.0,
            "closing_multiplier": 1.2    # Wider near close
        })

    def calculate_initial_sl(
        self,
        entry_price: float,
        position_type: str,
        atr: float = 0
    ) -> StopLossLevel:
        """
        Calculate initial stop loss

        Args:
            entry_price: Entry price
            position_type: 'LONG' or 'SHORT'
            atr: Average True Range (optional, for volatility-based SL)
        """
        # Use ATR if available, otherwise percentage
        if atr > 0:
            sl_distance = 2 * atr
        else:
            sl_distance = entry_price * (self.initial_sl_pct / 100)

        # Apply time-based multiplier
        multiplier = self._get_time_multiplier()
        sl_distance *= multiplier

        if position_type == "LONG":
            sl_price = entry_price - sl_distance
        else:  # SHORT
            sl_price = entry_price + sl_distance

        return StopLossLevel(
            price=round(sl_price, 2),
            reason=f"Initial SL ({self.initial_sl_pct}% * {multiplier:.1f}x time adj)",
            timestamp=datetime.now()
        )

    def update_trailing_sl(
        self,
        entry_price: float,
        current_price: float,
        current_sl: float,
        position_type: str
    ) -> StopLossLevel:
        """
        Update stop loss based on trailing logic

        Returns new SL if it should be updated, else returns current SL
        """
        if position_type == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Check if we should start trailing
            if pnl_pct >= self.trailing_start_pct:
                # Trail by trail_pct below current price
                new_sl = current_price * (1 - self.trail_pct / 100)

                # Only update if new SL is higher (for LONG)
                if new_sl > current_sl:
                    return StopLossLevel(
                        price=round(new_sl, 2),
                        reason=f"Trailing SL (profit {pnl_pct:.1f}%)",
                        timestamp=datetime.now()
                    )

        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

            if pnl_pct >= self.trailing_start_pct:
                new_sl = current_price * (1 + self.trail_pct / 100)

                # Only update if new SL is lower (for SHORT)
                if new_sl < current_sl:
                    return StopLossLevel(
                        price=round(new_sl, 2),
                        reason=f"Trailing SL (profit {pnl_pct:.1f}%)",
                        timestamp=datetime.now()
                    )

        # Return current SL unchanged
        return StopLossLevel(
            price=current_sl,
            reason="No change",
            timestamp=datetime.now()
        )

    def should_exit(
        self,
        current_price: float,
        stop_loss: float,
        position_type: str
    ) -> bool:
        """Check if stop loss is hit"""
        if position_type == "LONG":
            return current_price <= stop_loss
        else:  # SHORT
            return current_price >= stop_loss

    def _get_time_multiplier(self) -> float:
        """Get time-based SL multiplier"""
        now = datetime.now().time()

        # Morning session (9:15 - 11:30)
        if time(9, 15) <= now < time(11, 30):
            return self.time_multipliers.get("morning_multiplier", 0.8)

        # Midday (11:30 - 14:00)
        elif time(11, 30) <= now < time(14, 0):
            return self.time_multipliers.get("midday_multiplier", 1.0)

        # Closing session (14:00 - 15:30)
        else:
            return self.time_multipliers.get("closing_multiplier", 1.2)

    def calculate_breakeven_sl(
        self,
        entry_price: float,
        current_price: float,
        position_type: str,
        commission: float = 20
    ) -> StopLossLevel:
        """
        Move SL to breakeven (entry price + commission)
        Only if in sufficient profit
        """
        if position_type == "LONG":
            pnl = current_price - entry_price
            if pnl > commission * 2:
                be_price = entry_price + (commission / 100)  # Rough adjustment
                return StopLossLevel(
                    price=round(be_price, 2),
                    reason="Breakeven SL",
                    timestamp=datetime.now()
                )
        else:
            pnl = entry_price - current_price
            if pnl > commission * 2:
                be_price = entry_price - (commission / 100)
                return StopLossLevel(
                    price=round(be_price, 2),
                    reason="Breakeven SL",
                    timestamp=datetime.now()
                )

        return None
