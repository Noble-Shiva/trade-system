"""
Option Chain Analyzer - Analyze option chain data for strategy selection
"""

from dataclasses import dataclass
from typing import Optional
import math
from loguru import logger


@dataclass
class OptionData:
    strike: float
    call_price: float
    put_price: float
    call_oi: int
    put_oi: int
    call_volume: int
    put_volume: int
    call_iv: float = 0.0
    put_iv: float = 0.0


@dataclass
class StrategyLegs:
    """Legs for an options strategy"""
    buy_call: Optional[OptionData] = None
    sell_call: Optional[OptionData] = None
    buy_put: Optional[OptionData] = None
    sell_put: Optional[OptionData] = None
    max_profit: float = 0
    max_loss: float = 0
    breakeven_upper: float = 0
    breakeven_lower: float = 0


class OptionChainAnalyzer:
    """Analyze option chain for strategy opportunities"""

    def __init__(self, chain_data: dict, spot_price: float):
        self.chain_data = chain_data
        self.spot_price = spot_price
        self.options = self._parse_chain()

    def _parse_chain(self) -> list[OptionData]:
        """Parse raw chain data into OptionData objects"""
        options = []

        # Handle NSE format
        if isinstance(self.chain_data, list):
            for item in self.chain_data:
                strike = item.get("strikePrice", 0)
                ce = item.get("CE", {})
                pe = item.get("PE", {})

                if strike > 0:
                    options.append(OptionData(
                        strike=strike,
                        call_price=ce.get("lastPrice", 0),
                        put_price=pe.get("lastPrice", 0),
                        call_oi=ce.get("openInterest", 0),
                        put_oi=pe.get("openInterest", 0),
                        call_volume=ce.get("totalTradedVolume", 0),
                        put_volume=pe.get("totalTradedVolume", 0),
                        call_iv=ce.get("impliedVolatility", 0),
                        put_iv=pe.get("impliedVolatility", 0)
                    ))

        # Handle broker format
        elif isinstance(self.chain_data, dict):
            calls = self.chain_data.get("calls", [])
            puts = self.chain_data.get("puts", [])

            strikes = set([c["strike"] for c in calls] + [p["strike"] for p in puts])

            for strike in sorted(strikes):
                call = next((c for c in calls if c["strike"] == strike), {})
                put = next((p for p in puts if p["strike"] == strike), {})

                options.append(OptionData(
                    strike=strike,
                    call_price=call.get("last_price", 0),
                    put_price=put.get("last_price", 0),
                    call_oi=call.get("oi", 0),
                    put_oi=put.get("oi", 0),
                    call_volume=call.get("volume", 0),
                    put_volume=put.get("volume", 0)
                ))

        return sorted(options, key=lambda x: x.strike)

    def get_atm_strike(self) -> float:
        """Get ATM (At-The-Money) strike price"""
        if not self.options:
            return self.spot_price

        # Find strike closest to spot
        return min(self.options, key=lambda x: abs(x.strike - self.spot_price)).strike

    def find_iron_condor(
        self,
        min_premium: float = 50,
        delta_range: tuple = (0.15, 0.25),
        spread_width: float = 100
    ) -> Optional[StrategyLegs]:
        """
        Find optimal Iron Condor setup

        Args:
            min_premium: Minimum net premium required
            delta_range: Preferred delta range for short strikes
            spread_width: Width between short and long strikes

        Returns:
            StrategyLegs with the 4 legs or None if no good setup
        """
        try:
            atm = self.get_atm_strike()

            # Find OTM strikes based on delta (approximated by distance from ATM)
            # Typically 0.15-0.25 delta is 1-2 standard deviations away
            distance = self.spot_price * 0.02  # ~2% for moderate delta

            # Short call strike (above spot)
            sell_call_strike = atm + distance
            sell_call = self._find_nearest_strike(sell_call_strike)

            # Long call strike (further OTM)
            buy_call_strike = sell_call.strike + spread_width
            buy_call = self._find_nearest_strike(buy_call_strike)

            # Short put strike (below spot)
            sell_put_strike = atm - distance
            sell_put = self._find_nearest_strike(sell_put_strike)

            # Long put strike (further OTM)
            buy_put_strike = sell_put.strike - spread_width
            buy_put = self._find_nearest_strike(buy_put_strike)

            if not all([sell_call, buy_call, sell_put, buy_put]):
                return None

            # Calculate premiums
            net_premium = (
                sell_call.call_price - buy_call.call_price +
                sell_put.put_price - buy_put.put_price
            )

            if net_premium < min_premium:
                logger.info(f"Iron Condor premium {net_premium} below minimum {min_premium}")
                return None

            # Calculate risk/reward
            max_profit = net_premium
            max_loss = spread_width - net_premium

            return StrategyLegs(
                buy_call=buy_call,
                sell_call=sell_call,
                buy_put=buy_put,
                sell_put=sell_put,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_upper=sell_call.strike + net_premium,
                breakeven_lower=sell_put.strike - net_premium
            )

        except Exception as e:
            logger.error(f"Error finding Iron Condor: {e}")
            return None

    def find_bull_put_spread(
        self,
        min_premium: float = 30,
        spread_width: float = 100
    ) -> Optional[StrategyLegs]:
        """
        Find Bull Put Spread (credit spread, bullish)

        Sell higher strike put, buy lower strike put
        """
        try:
            atm = self.get_atm_strike()

            # Sell put slightly OTM
            sell_strike = atm - (self.spot_price * 0.01)  # ~1% below
            sell_put = self._find_nearest_strike(sell_strike)

            # Buy put further OTM
            buy_strike = sell_put.strike - spread_width
            buy_put = self._find_nearest_strike(buy_strike)

            if not sell_put or not buy_put:
                return None

            net_premium = sell_put.put_price - buy_put.put_price

            if net_premium < min_premium:
                return None

            return StrategyLegs(
                sell_put=sell_put,
                buy_put=buy_put,
                max_profit=net_premium,
                max_loss=spread_width - net_premium,
                breakeven_lower=sell_put.strike - net_premium
            )

        except Exception as e:
            logger.error(f"Error finding Bull Put Spread: {e}")
            return None

    def find_bear_call_spread(
        self,
        min_premium: float = 30,
        spread_width: float = 100
    ) -> Optional[StrategyLegs]:
        """
        Find Bear Call Spread (credit spread, bearish)

        Sell lower strike call, buy higher strike call
        """
        try:
            atm = self.get_atm_strike()

            # Sell call slightly OTM
            sell_strike = atm + (self.spot_price * 0.01)  # ~1% above
            sell_call = self._find_nearest_strike(sell_strike)

            # Buy call further OTM
            buy_strike = sell_call.strike + spread_width
            buy_call = self._find_nearest_strike(buy_strike)

            if not sell_call or not buy_call:
                return None

            net_premium = sell_call.call_price - buy_call.call_price

            if net_premium < min_premium:
                return None

            return StrategyLegs(
                sell_call=sell_call,
                buy_call=buy_call,
                max_profit=net_premium,
                max_loss=spread_width - net_premium,
                breakeven_upper=sell_call.strike + net_premium
            )

        except Exception as e:
            logger.error(f"Error finding Bear Call Spread: {e}")
            return None

    def _find_nearest_strike(self, target: float) -> Optional[OptionData]:
        """Find option with strike nearest to target"""
        if not self.options:
            return None
        return min(self.options, key=lambda x: abs(x.strike - target))

    def get_max_oi_strikes(self) -> dict:
        """Get strikes with maximum OI (support/resistance levels)"""
        if not self.options:
            return {"call": 0, "put": 0}

        max_call_oi = max(self.options, key=lambda x: x.call_oi)
        max_put_oi = max(self.options, key=lambda x: x.put_oi)

        return {
            "call": max_call_oi.strike,
            "put": max_put_oi.strike,
            "call_oi": max_call_oi.call_oi,
            "put_oi": max_put_oi.put_oi
        }

    def get_pcr(self) -> float:
        """Calculate Put-Call Ratio from OI"""
        total_call_oi = sum(opt.call_oi for opt in self.options)
        total_put_oi = sum(opt.put_oi for opt in self.options)

        if total_call_oi == 0:
            return 0

        return total_put_oi / total_call_oi
