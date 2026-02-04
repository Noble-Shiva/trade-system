"""
Base Strategy Class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class SignalType(Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADJUST = "ADJUST"
    HOLD = "HOLD"


@dataclass
class Signal:
    signal_type: SignalType
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    price: float
    stop_loss: float
    target: float
    reason: str
    timestamp: datetime = None
    metadata: dict = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class StrategyBase(ABC):
    """Abstract base class for all trading strategies"""

    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__
        self.positions = []

    @property
    @abstractmethod
    def strategy_type(self) -> str:
        """Type of strategy: 'iron_condor', 'spread', etc."""
        pass

    @property
    @abstractmethod
    def min_capital_required(self) -> float:
        """Minimum capital required for this strategy"""
        pass

    @abstractmethod
    def analyze(self, market_data: dict) -> list[Signal]:
        """
        Analyze market data and generate signals

        Args:
            market_data: Dict with spot_price, option_chain, indicators, etc.

        Returns:
            List of Signal objects for execution
        """
        pass

    @abstractmethod
    def calculate_position_size(self, capital: float, risk_per_trade: float) -> int:
        """
        Calculate number of lots based on capital and risk

        Args:
            capital: Available capital
            risk_per_trade: Max risk per trade as decimal (e.g., 0.02 for 2%)

        Returns:
            Number of lots
        """
        pass

    @abstractmethod
    def get_exit_signals(self, position: dict, current_price: float) -> Optional[Signal]:
        """
        Check if position should be exited

        Args:
            position: Current position details
            current_price: Current market price

        Returns:
            Exit signal if exit condition met, else None
        """
        pass

    def should_trade_today(self, market_data: dict) -> bool:
        """
        Check if strategy should trade today

        Default checks:
        - Not too close to expiry
        - VIX within acceptable range
        - Market conditions suitable
        """
        vix = market_data.get("vix", 15)

        # Don't trade in very high volatility
        if vix > 25:
            return False

        # Don't trade in very low volatility (low premium)
        if vix < 10:
            return False

        return True
