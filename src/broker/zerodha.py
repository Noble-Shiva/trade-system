"""
Zerodha Kite Connect Broker Implementation
"""

from datetime import datetime
from typing import Optional
from loguru import logger

from .base import (
    BrokerBase, Order, Position, Quote,
    OrderType, OrderSide, ProductType, Exchange
)


class ZerodhaBroker(BrokerBase):
    """Zerodha Kite Connect implementation"""

    def __init__(self, api_key: str, api_secret: str, user_id: str = None):
        super().__init__(api_key, api_secret, user_id)
        self.kite = None

    @property
    def name(self) -> str:
        return "zerodha"

    def login(self) -> bool:
        """
        Login to Zerodha Kite
        Note: Zerodha requires manual login via browser for access token
        """
        try:
            from kiteconnect import KiteConnect

            self.kite = KiteConnect(api_key=self.api_key)

            # If access token is provided directly (from previous session)
            if self.api_secret and len(self.api_secret) > 50:
                self.access_token = self.api_secret
                self.kite.set_access_token(self.access_token)
            else:
                # Generate login URL for manual authentication
                login_url = self.kite.login_url()
                logger.info(f"Please login at: {login_url}")
                logger.info("After login, you'll get a request_token in the redirect URL")

                # In production, this would be handled via webhook or manual input
                request_token = input("Enter request_token: ")
                data = self.kite.generate_session(request_token, api_secret=self.api_secret)
                self.access_token = data["access_token"]
                self.kite.set_access_token(self.access_token)

            self.is_authenticated = True
            logger.info("Zerodha login successful")
            return True

        except Exception as e:
            logger.error(f"Zerodha login failed: {e}")
            return False

    def _convert_exchange(self, exchange: str) -> str:
        """Convert our exchange enum to Zerodha format"""
        mapping = {
            "BSE": "BSE",
            "NSE": "NSE",
            "NFO": "NFO",
            "BFO": "BFO"
        }
        return mapping.get(exchange, exchange)

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert order type to Zerodha format"""
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "SL",
            OrderType.SL_M: "SL-M"
        }
        return mapping.get(order_type, "MARKET")

    def _convert_product(self, product: ProductType) -> str:
        """Convert product type to Zerodha format"""
        mapping = {
            ProductType.NRML: "NRML",
            ProductType.MIS: "MIS",
            ProductType.CNC: "CNC"
        }
        return mapping.get(product, "NRML")

    def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Get current quote for a symbol"""
        try:
            exchange = self._convert_exchange(exchange)
            instrument = f"{exchange}:{symbol}"
            data = self.kite.quote([instrument])[instrument]

            return Quote(
                symbol=symbol,
                last_price=data["last_price"],
                bid=data["depth"]["buy"][0]["price"] if data["depth"]["buy"] else 0,
                ask=data["depth"]["sell"][0]["price"] if data["depth"]["sell"] else 0,
                volume=data["volume"],
                open=data["ohlc"]["open"],
                high=data["ohlc"]["high"],
                low=data["ohlc"]["low"],
                close=data["ohlc"]["close"],
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise

    def get_option_chain(self, symbol: str, expiry: str) -> dict:
        """
        Get option chain for an index
        Note: Zerodha doesn't have direct option chain API,
        we fetch from instruments and quotes
        """
        try:
            # Get all instruments for the symbol
            instruments = self.kite.instruments("NFO" if symbol in ["NIFTY", "BANKNIFTY"] else "BFO")

            # Filter for the symbol and expiry
            options = []
            for inst in instruments:
                if (inst["name"] == symbol and
                    inst["expiry"].strftime("%Y-%m-%d") == expiry and
                    inst["instrument_type"] in ["CE", "PE"]):
                    options.append(inst)

            # Get quotes for all options
            option_symbols = [f"NFO:{opt['tradingsymbol']}" for opt in options]

            # Batch quotes (Zerodha allows up to 500)
            quotes = {}
            for i in range(0, len(option_symbols), 500):
                batch = option_symbols[i:i+500]
                quotes.update(self.kite.quote(batch))

            # Build option chain
            chain = {"calls": [], "puts": []}
            for opt in options:
                key = f"NFO:{opt['tradingsymbol']}"
                if key in quotes:
                    q = quotes[key]
                    data = {
                        "strike": opt["strike"],
                        "symbol": opt["tradingsymbol"],
                        "last_price": q["last_price"],
                        "bid": q["depth"]["buy"][0]["price"] if q["depth"]["buy"] else 0,
                        "ask": q["depth"]["sell"][0]["price"] if q["depth"]["sell"] else 0,
                        "volume": q["volume"],
                        "oi": q["oi"],
                        "oi_change": q.get("oi_day_change", 0)
                    }
                    if opt["instrument_type"] == "CE":
                        chain["calls"].append(data)
                    else:
                        chain["puts"].append(data)

            # Sort by strike
            chain["calls"].sort(key=lambda x: x["strike"])
            chain["puts"].sort(key=lambda x: x["strike"])

            return chain

        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
            raise

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
        """Place an order"""
        try:
            order_id = self.kite.place_order(
                variety="regular",
                exchange=self._convert_exchange(exchange),
                tradingsymbol=symbol,
                transaction_type=side.value,
                quantity=quantity,
                product=self._convert_product(product),
                order_type=self._convert_order_type(order_type),
                price=price if order_type == OrderType.LIMIT else None,
                trigger_price=trigger_price if order_type in [OrderType.SL, OrderType.SL_M] else None
            )

            logger.info(f"Order placed: {order_id} - {side.value} {quantity} {symbol}")

            return Order(
                order_id=str(order_id),
                symbol=symbol,
                exchange=exchange,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                product=product,
                status="PENDING"
            )

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def modify_order(
        self,
        order_id: str,
        price: float = None,
        trigger_price: float = None,
        quantity: int = None
    ) -> Order:
        """Modify an existing order"""
        try:
            params = {"variety": "regular", "order_id": order_id}
            if price is not None:
                params["price"] = price
            if trigger_price is not None:
                params["trigger_price"] = trigger_price
            if quantity is not None:
                params["quantity"] = quantity

            self.kite.modify_order(**params)
            logger.info(f"Order modified: {order_id}")

            return self.get_order_status(order_id)

        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.kite.cancel_order(variety="regular", order_id=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        try:
            orders = self.kite.orders()
            for o in orders:
                if str(o["order_id"]) == str(order_id):
                    return Order(
                        order_id=str(o["order_id"]),
                        symbol=o["tradingsymbol"],
                        exchange=o["exchange"],
                        side=OrderSide(o["transaction_type"]),
                        order_type=OrderType(o["order_type"]),
                        quantity=o["quantity"],
                        price=o["price"],
                        trigger_price=o.get("trigger_price", 0),
                        product=ProductType(o["product"]),
                        status=o["status"],
                        filled_quantity=o["filled_quantity"],
                        average_price=o["average_price"],
                        timestamp=o["order_timestamp"]
                    )
            raise ValueError(f"Order {order_id} not found")
        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            raise

    def get_positions(self) -> list[Position]:
        """Get all open positions"""
        try:
            positions = self.kite.positions()["net"]
            result = []

            for p in positions:
                if p["quantity"] != 0:
                    result.append(Position(
                        symbol=p["tradingsymbol"],
                        exchange=p["exchange"],
                        quantity=p["quantity"],
                        average_price=p["average_price"],
                        last_price=p["last_price"],
                        pnl=p["pnl"],
                        product=ProductType(p["product"])
                    ))

            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    def get_margins(self) -> dict:
        """Get available margins"""
        try:
            margins = self.kite.margins()
            equity = margins.get("equity", {})

            return {
                "available": equity.get("available", {}).get("live_balance", 0),
                "used": equity.get("utilised", {}).get("debits", 0),
                "total": equity.get("net", 0)
            }
        except Exception as e:
            logger.error(f"Error getting margins: {e}")
            raise

    def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime
    ) -> list[dict]:
        """Get historical OHLCV data"""
        try:
            # Get instrument token
            instruments = self.kite.instruments(self._convert_exchange(exchange))
            instrument_token = None
            for inst in instruments:
                if inst["tradingsymbol"] == symbol:
                    instrument_token = inst["instrument_token"]
                    break

            if not instrument_token:
                raise ValueError(f"Instrument {symbol} not found")

            # Map interval
            interval_map = {
                "1minute": "minute",
                "5minute": "5minute",
                "15minute": "15minute",
                "day": "day"
            }
            kite_interval = interval_map.get(interval, "day")

            data = self.kite.historical_data(
                instrument_token,
                from_date,
                to_date,
                kite_interval
            )

            return [
                {
                    "timestamp": d["date"],
                    "open": d["open"],
                    "high": d["high"],
                    "low": d["low"],
                    "close": d["close"],
                    "volume": d["volume"]
                }
                for d in data
            ]

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            raise
