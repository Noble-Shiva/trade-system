"""
Base Broker Interface - Abstract adapter pattern for multiple brokers
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss
    SL_M = "SL-M"  # Stop Loss Market


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    NRML = "NRML"  # Normal (overnight)
    MIS = "MIS"  # Intraday
    CNC = "CNC"  # Delivery


class Exchange(Enum):
    BSE = "BSE"
    NSE = "NSE"
    NFO = "NFO"  # NSE F&O
    BFO = "BFO"  # BSE F&O


@dataclass
class Order:
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    trigger_price: float = 0.0
    product: ProductType = ProductType.NRML
    status: str = "PENDING"
    filled_quantity: int = 0
    average_price: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: ProductType


@dataclass
class Quote:
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume: int
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime


class BrokerBase(ABC):
    """Abstract base class for all broker implementations"""

    def __init__(self, api_key: str, api_secret: str, user_id: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.user_id = user_id
        self.access_token = None
        self.is_authenticated = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier"""
        pass

    @abstractmethod
    def login(self) -> bool:
        """
        Authenticate with the broker
        Returns True if successful
        """
        pass

    @abstractmethod
    def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Get current quote for a symbol"""
        pass

    @abstractmethod
    def get_option_chain(self, symbol: str, expiry: str) -> dict:
        """
        Get option chain for an index/stock
        Returns dict with calls and puts data
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        exchange: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: float = 0.0,
        trigger_price: float = 0.0,
        product: ProductType = ProductType.NRML
    ) -> Order:
        """Place an order and return Order object"""
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        price: float = None,
        trigger_price: float = None,
        quantity: int = None
    ) -> Order:
        """Modify an existing order"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order, returns True if successful"""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """Get current status of an order"""
        pass

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Get all open positions"""
        pass

    @abstractmethod
    def get_margins(self) -> dict:
        """
        Get available margins
        Returns dict with 'available', 'used', 'total'
        """
        pass

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime
    ) -> list[dict]:
        """
        Get historical OHLCV data
        interval: '1minute', '5minute', '15minute', 'day'
        """
        pass

    def square_off_all(self) -> list[Order]:
        """Square off all open positions"""
        orders = []
        positions = self.get_positions()

        for pos in positions:
            if pos.quantity != 0:
                side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
                qty = abs(pos.quantity)

                order = self.place_order(
                    symbol=pos.symbol,
                    exchange=pos.exchange,
                    side=side,
                    quantity=qty,
                    order_type=OrderType.MARKET,
                    product=pos.product
                )
                orders.append(order)

        return orders
