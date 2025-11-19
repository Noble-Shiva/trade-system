"""
Spread Strategies - Bull Put Spread and Bear Call Spread
"""

from typing import Optional
from loguru import logger

from .base import StrategyBase, Signal, SignalType
from ..data.option_chain import OptionChainAnalyzer


class BullPutSpreadStrategy(StrategyBase):
    """
    Bull Put Spread: Sell higher strike put, buy lower strike put

    Best for: Moderately bullish outlook
    Risk: Limited (spread width - premium)
    Reward: Limited (net premium)
    """

    @property
    def strategy_type(self) -> str:
        return "bull_put_spread"

    @property
    def min_capital_required(self) -> float:
        return 10000

    def __init__(self, config: dict):
        super().__init__(config)
        self.spread_width = config.get("spread_width", 100)
        self.min_premium = config.get("min_premium", 30)
        self.target_profit_pct = config.get("target_profit_pct", 50)
        self.max_loss_pct = config.get("max_loss_pct", 100)

    def analyze(self, market_data: dict) -> list[Signal]:
        """Analyze and generate Bull Put Spread signals"""
        signals = []

        spot_price = market_data.get("spot_price", 0)
        chain_data = market_data.get("option_chain", {})
        symbol = market_data.get("symbol", "NIFTY")
        trend = market_data.get("trend", "neutral")

        # Only trade in bullish/neutral conditions
        if trend == "bearish":
            logger.info("Market bearish, skipping Bull Put Spread")
            return signals

        analyzer = OptionChainAnalyzer(chain_data, spot_price)
        legs = analyzer.find_bull_put_spread(
            min_premium=self.min_premium,
            spread_width=self.spread_width
        )

        if not legs:
            logger.info("No suitable Bull Put Spread found")
            return signals

        risk_reward = legs.max_profit / legs.max_loss if legs.max_loss > 0 else 0

        if risk_reward < 0.25:
            return signals

        # Sell Put (higher strike)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.sell_put.strike)}PE",
            action="SELL",
            quantity=1,
            price=legs.sell_put.put_price,
            stop_loss=legs.sell_put.put_price * 2,
            target=legs.sell_put.put_price * 0.5,
            reason=f"Bull Put Spread - Sell @ {legs.sell_put.strike}",
            metadata={"strategy": "bull_put_spread", "leg": "sell_put"}
        ))

        # Buy Put (lower strike)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.buy_put.strike)}PE",
            action="BUY",
            quantity=1,
            price=legs.buy_put.put_price,
            stop_loss=0,
            target=0,
            reason=f"Bull Put Spread - Buy @ {legs.buy_put.strike}",
            metadata={"strategy": "bull_put_spread", "leg": "buy_put"}
        ))

        logger.info(
            f"Bull Put Spread: Max Profit={legs.max_profit:.0f}, "
            f"Max Loss={legs.max_loss:.0f}"
        )

        return signals

    def calculate_position_size(self, capital: float, risk_per_trade: float) -> int:
        max_risk = capital * risk_per_trade
        return max(1, int(max_risk / self.spread_width))

    def get_exit_signals(self, position: dict, current_price: float) -> Optional[Signal]:
        entry_price = position.get("entry_price", 0)
        if not entry_price:
            return None

        pnl_pct = ((entry_price - current_price) / entry_price) * 100

        if "SELL" in position.get("type", ""):
            if pnl_pct >= self.target_profit_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Target hit: {pnl_pct:.1f}%"
                )

            if pnl_pct <= -self.max_loss_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Stop loss: {pnl_pct:.1f}%"
                )

        return None


class BearCallSpreadStrategy(StrategyBase):
    """
    Bear Call Spread: Sell lower strike call, buy higher strike call

    Best for: Moderately bearish outlook
    Risk: Limited
    Reward: Limited (net premium)
    """

    @property
    def strategy_type(self) -> str:
        return "bear_call_spread"

    @property
    def min_capital_required(self) -> float:
        return 10000

    def __init__(self, config: dict):
        super().__init__(config)
        self.spread_width = config.get("spread_width", 100)
        self.min_premium = config.get("min_premium", 30)
        self.target_profit_pct = config.get("target_profit_pct", 50)
        self.max_loss_pct = config.get("max_loss_pct", 100)

    def analyze(self, market_data: dict) -> list[Signal]:
        """Analyze and generate Bear Call Spread signals"""
        signals = []

        spot_price = market_data.get("spot_price", 0)
        chain_data = market_data.get("option_chain", {})
        symbol = market_data.get("symbol", "NIFTY")
        trend = market_data.get("trend", "neutral")

        # Only trade in bearish/neutral conditions
        if trend == "bullish":
            logger.info("Market bullish, skipping Bear Call Spread")
            return signals

        analyzer = OptionChainAnalyzer(chain_data, spot_price)
        legs = analyzer.find_bear_call_spread(
            min_premium=self.min_premium,
            spread_width=self.spread_width
        )

        if not legs:
            return signals

        risk_reward = legs.max_profit / legs.max_loss if legs.max_loss > 0 else 0

        if risk_reward < 0.25:
            return signals

        # Sell Call (lower strike)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.sell_call.strike)}CE",
            action="SELL",
            quantity=1,
            price=legs.sell_call.call_price,
            stop_loss=legs.sell_call.call_price * 2,
            target=legs.sell_call.call_price * 0.5,
            reason=f"Bear Call Spread - Sell @ {legs.sell_call.strike}",
            metadata={"strategy": "bear_call_spread", "leg": "sell_call"}
        ))

        # Buy Call (higher strike)
        signals.append(Signal(
            signal_type=SignalType.ENTRY,
            symbol=f"{symbol}{int(legs.buy_call.strike)}CE",
            action="BUY",
            quantity=1,
            price=legs.buy_call.call_price,
            stop_loss=0,
            target=0,
            reason=f"Bear Call Spread - Buy @ {legs.buy_call.strike}",
            metadata={"strategy": "bear_call_spread", "leg": "buy_call"}
        ))

        logger.info(
            f"Bear Call Spread: Max Profit={legs.max_profit:.0f}, "
            f"Max Loss={legs.max_loss:.0f}"
        )

        return signals

    def calculate_position_size(self, capital: float, risk_per_trade: float) -> int:
        max_risk = capital * risk_per_trade
        return max(1, int(max_risk / self.spread_width))

    def get_exit_signals(self, position: dict, current_price: float) -> Optional[Signal]:
        entry_price = position.get("entry_price", 0)
        if not entry_price:
            return None

        pnl_pct = ((entry_price - current_price) / entry_price) * 100

        if "SELL" in position.get("type", ""):
            if pnl_pct >= self.target_profit_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Target hit: {pnl_pct:.1f}%"
                )

            if pnl_pct <= -self.max_loss_pct:
                return Signal(
                    signal_type=SignalType.EXIT,
                    symbol=position["symbol"],
                    action="BUY",
                    quantity=position["quantity"],
                    price=current_price,
                    stop_loss=0,
                    target=0,
                    reason=f"Stop loss: {pnl_pct:.1f}%"
                )

        return None
