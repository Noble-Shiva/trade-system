"""
Iron Condor Strategy - Neutral strategy for range-bound markets
"""

from typing import Optional
from datetime import datetime
from loguru import logger

from .base import StrategyBase, Signal, SignalType
from ..data.option_chain import OptionChainAnalyzer


class IronCondorStrategy(StrategyBase):
    """
    Iron Condor: Sell OTM call + put, buy further OTM call + put

    Best for: Range-bound, low-moderate volatility markets
    Risk: Limited
    Reward: Limited (net premium)
    """

    @property
    def strategy_type(self) -> str:
        return "iron_condor"

    @property
    def min_capital_required(self) -> float:
        return 15000  # Minimum for 1 lot

    def __init__(self, config: dict):
        super().__init__(config)
        self.spread_width = config.get("spread_width", 100)
        self.min_premium = config.get("min_premium", 50)
        self.target_profit_pct = config.get("target_profit_pct", 50)  # Exit at 50% of max profit
        self.max_loss_pct = config.get("max_loss_pct", 100)  # Exit at 100% of premium (2x loss)

    def analyze(self, market_data: dict) -> list[Signal]:
        """Analyze and generate Iron Condor signals"""
        signals = []

        spot_price = market_data.get("spot_price", 0)
        chain_data = market_data.get("option_chain", {})
        symbol = market_data.get("symbol", "NIFTY")

        if not spot_price or not chain_data:
            logger.warning("Missing market data for Iron Condor analysis")
            return signals

        # Analyze option chain
        analyzer = OptionChainAnalyzer(chain_data, spot_price)

        # Find optimal Iron Condor setup
        legs = analyzer.find_iron_condor(
            min_premium=self.min_premium,
            spread_width=self.spread_width
        )

        if not legs:
            logger.info("No suitable Iron Condor setup found")
            return signals

        # Check if setup meets criteria
        risk_reward = legs.max_profit / legs.max_loss if legs.max_loss > 0 else 0

        if risk_reward < 0.3:  # At least 1:3 risk-reward
            logger.info(f"Iron Condor risk-reward {risk_reward:.2f} too low")
            return signals

        # Generate signals for all 4 legs
        # 1. Sell Call
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.sell_call.strike)}CE",
            action="SELL",
            quantity=1,
            price=legs.sell_call.call_price,
            stop_loss=legs.sell_call.call_price * 2,  # 100% SL
            target=legs.sell_call.call_price * 0.5,  # 50% target
            reason=f"Iron Condor - Sell Call @ {legs.sell_call.strike}",
            metadata={
                "strategy": "iron_condor",
                "leg": "sell_call",
                "strike": legs.sell_call.strike
            }
        ))

        # 2. Buy Call (hedge)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.buy_call.strike)}CE",
            action="BUY",
            quantity=1,
            price=legs.buy_call.call_price,
            stop_loss=0,
            target=0,
            reason=f"Iron Condor - Buy Call @ {legs.buy_call.strike}",
            metadata={
                "strategy": "iron_condor",
                "leg": "buy_call",
                "strike": legs.buy_call.strike
            }
        ))

        # 3. Sell Put
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.sell_put.strike)}PE",
            action="SELL",
            quantity=1,
            price=legs.sell_put.put_price,
            stop_loss=legs.sell_put.put_price * 2,
            target=legs.sell_put.put_price * 0.5,
            reason=f"Iron Condor - Sell Put @ {legs.sell_put.strike}",
            metadata={
                "strategy": "iron_condor",
                "leg": "sell_put",
                "strike": legs.sell_put.strike
            }
        ))

        # 4. Buy Put (hedge)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.buy_put.strike)}PE",
            action="BUY",
            quantity=1,
            price=legs.buy_put.put_price,
            stop_loss=0,
            target=0,
            reason=f"Iron Condor - Buy Put @ {legs.buy_put.strike}",
            metadata={
                "strategy": "iron_condor",
                "leg": "buy_put",
                "strike": legs.buy_put.strike
            }
        ))

        logger.info(
            f"Iron Condor signals generated: "
            f"Max Profit={legs.max_profit:.0f}, "
            f"Max Loss={legs.max_loss:.0f}, "
            f"R:R={risk_reward:.2f}"
        )

        return signals

    def calculate_position_size(self, capital: float, risk_per_trade: float) -> int:
        """Calculate number of lots"""
        max_risk = capital * risk_per_trade
        risk_per_lot = self.spread_width  # Max loss per lot

        lots = int(max_risk / risk_per_lot)
        return max(1, lots)  # At least 1 lot

    def get_exit_signals(self, position: dict, current_price: float) -> Optional[Signal]:
        """Check if position should be exited"""
        entry_price = position.get("entry_price", 0)
        position_type = position.get("type", "")

        if not entry_price:
            return None

        pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # For sold options, profit when price decreases
        if "SELL" in position_type:
            # Target hit (50% of premium captured)
            if pnl_pct >= self.target_profit_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",  # Buy back to close
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Target hit: {pnl_pct:.1f}% profit"
                )

            # Stop loss hit
            if pnl_pct <= -self.max_loss_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Stop loss hit: {pnl_pct:.1f}% loss"
                )

        return None
