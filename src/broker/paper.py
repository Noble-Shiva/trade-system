"""
Paper Trading Broker - Simulates trades without real money
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from loguru import logger

from .base import BrokerBase, OrderType, OrderSide, ProductType


@dataclass
class PaperOrder:
    """Simulated order"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    order_type: OrderType
    product_type: ProductType
    status: str = "PENDING"
    filled_price: float = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PaperPosition:
    """Simulated position"""
    symbol: str
    quantity: int
    avg_price: float
    side: str  # LONG or SHORT
    pnl: float = 0
    current_price: float = 0


class PaperBroker(BrokerBase):
    """
    Paper trading broker that simulates trades
    
    - No real money at risk
    - Simulates order execution with slippage
    - Tracks positions and P&L
    - Logs all trades for review
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        slippage_pct: float = 0.1,
        commission_per_order: float = 20
    ):
        # Don't call super().__init__ - it needs credentials
        self.api_key = "PAPER"
        self.api_secret = "PAPER"
        self.access_token = "PAPER_TOKEN"
        self.is_authenticated = True
        
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.slippage_pct = slippage_pct
        self.commission = commission_per_order
        
        self.orders: List[PaperOrder] = []
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_log: List[dict] = []
        self.order_counter = 0
        
        logger.info(f"📝 Paper Broker initialized with ₹{initial_capital:,.0f}")
    
    @property
    def name(self) -> str:
        return "paper"
    
    def login(self) -> bool:
        """Paper broker is always logged in"""
        logger.info("📝 Paper Broker: Login simulated")
        return True
    
    def get_margins(self) -> dict:
        """Get simulated margins"""
        return {
            "available": self.capital,
            "used": 0,
            "total": self.capital
        }
    
    def get_historical_data(self, symbol: str, exchange: str, interval: str, 
                           from_date: datetime, to_date: datetime) -> list:
        """Historical data not available in paper mode"""
        logger.warning("📝 Paper Broker: Historical data not available, use DataFetcher")
        return []
    
    def connect(self) -> bool:
        """Simulate connection"""
        logger.info("📝 Paper Broker: Connected (simulated)")
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        logger.info("📝 Paper Broker: Disconnected")
    
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float,
        order_type: OrderType = OrderType.LIMIT,
        product_type: ProductType = ProductType.MIS
    ) -> Optional[str]:
        """
        Simulate order placement
        
        Returns order_id if successful
        """
        self.order_counter += 1
        order_id = f"PAPER_{self.order_counter:06d}"
        
        # Apply slippage
        if side == OrderSide.BUY:
            exec_price = price * (1 + self.slippage_pct / 100)
        else:
            exec_price = price * (1 - self.slippage_pct / 100)
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            product_type=product_type,
            status="COMPLETE",
            filled_price=exec_price
        )
        
        self.orders.append(order)
        
        # Update position
        self._update_position(order)
        
        # Deduct commission
        self.capital -= self.commission
        
        # Log trade
        self.trade_log.append({
            "timestamp": datetime.now().isoformat(),
            "order_id": order_id,
            "symbol": symbol,
            "side": side.value,
            "quantity": quantity,
            "price": price,
            "exec_price": exec_price,
            "commission": self.commission
        })
        
        logger.info(f"📝 Paper Order: {side.value} {quantity}x {symbol} @ ₹{exec_price:.2f}")
        
        return order_id
    
    def _update_position(self, order: PaperOrder):
        """Update position after order fill"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # New position
            side = "LONG" if order.side == OrderSide.BUY else "SHORT"
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=order.quantity,
                avg_price=order.filled_price,
                side=side,
                current_price=order.filled_price
            )
        else:
            # Existing position
            pos = self.positions[symbol]
            
            if (order.side == OrderSide.BUY and pos.side == "LONG") or \
               (order.side == OrderSide.SELL and pos.side == "SHORT"):
                # Adding to position
                total_qty = pos.quantity + order.quantity
                pos.avg_price = (pos.avg_price * pos.quantity + order.filled_price * order.quantity) / total_qty
                pos.quantity = total_qty
            else:
                # Reducing position
                if order.quantity >= pos.quantity:
                    # Close position
                    pnl = self._calculate_pnl(pos, order.filled_price)
                    self.capital += pnl
                    logger.info(f"📝 Position closed: {symbol} P&L: ₹{pnl:.2f}")
                    del self.positions[symbol]
                else:
                    # Partial close
                    pnl = self._calculate_pnl(pos, order.filled_price, order.quantity)
                    self.capital += pnl
                    pos.quantity -= order.quantity
    
    def _calculate_pnl(self, pos: PaperPosition, exit_price: float, qty: int = None) -> float:
        """Calculate P&L for a position"""
        qty = qty or pos.quantity
        
        if pos.side == "LONG":
            return (exit_price - pos.avg_price) * qty
        else:
            return (pos.avg_price - exit_price) * qty
    
    def modify_order(self, order_id: str, price: float = None, quantity: int = None) -> bool:
        """Paper trading doesn't support order modification"""
        logger.warning("📝 Paper Broker: Order modification not supported")
        return False
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        for order in self.orders:
            if order.order_id == order_id and order.status == "PENDING":
                order.status = "CANCELLED"
                return True
        return False
    
    def get_order_status(self, order_id: str) -> dict:
        """Get status of an order"""
        for order in self.orders:
            if order.order_id == order_id:
                return {
                    "order_id": order.order_id,
                    "status": order.status,
                    "filled_price": order.filled_price
                }
        return {}
    
    def get_positions(self) -> List[dict]:
        """Get all open positions"""
        return [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "side": pos.side,
                "pnl": pos.pnl,
                "current_price": pos.current_price
            }
            for pos in self.positions.values()
        ]
    
    def get_quote(self, symbol: str) -> dict:
        """Get current quote (simulated)"""
        # In paper trading, return last known price
        if symbol in self.positions:
            return {
                "symbol": symbol,
                "ltp": self.positions[symbol].current_price,
                "bid": self.positions[symbol].current_price * 0.999,
                "ask": self.positions[symbol].current_price * 1.001
            }
        return {"symbol": symbol, "ltp": 0, "bid": 0, "ask": 0}
    
    def get_option_chain(self, symbol: str) -> dict:
        """Get option chain (not available in paper mode)"""
        logger.warning("📝 Paper Broker: Option chain not available, use DataFetcher")
        return {}
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for positions"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.current_price = price
                pos.pnl = self._calculate_pnl(pos, price)
    
    def get_summary(self) -> dict:
        """Get trading summary"""
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.capital,
            "open_pnl": total_pnl,
            "total_pnl": (self.capital - self.initial_capital) + total_pnl,
            "total_orders": len(self.orders),
            "open_positions": len(self.positions),
            "commission_paid": len(self.orders) * self.commission
        }
    
    def print_summary(self):
        """Print trading summary to console"""
        summary = self.get_summary()
        
        print("\n" + "=" * 50)
        print("📝 PAPER TRADING SUMMARY")
        print("=" * 50)
        print(f"Initial Capital: ₹{summary['initial_capital']:,.2f}")
        print(f"Current Capital: ₹{summary['current_capital']:,.2f}")
        print(f"Open P&L:        ₹{summary['open_pnl']:,.2f}")
        print(f"Total P&L:       ₹{summary['total_pnl']:,.2f}")
        print(f"Total Orders:    {summary['total_orders']}")
        print(f"Open Positions:  {summary['open_positions']}")
        print(f"Commission Paid: ₹{summary['commission_paid']:,.2f}")
        print("=" * 50)
