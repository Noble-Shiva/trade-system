"""
Angel One (Angel Broking) SmartAPI Implementation
"""

from datetime import datetime
from typing import Optional
from loguru import logger

from .base import (
    BrokerBase, Order, Position, Quote,
    OrderType, OrderSide, ProductType, Exchange
)


class AngelOneBroker(BrokerBase):
    """Angel One SmartAPI implementation"""

    def __init__(self, api_key: str, api_secret: str, user_id: str = None):
        super().__init__(api_key, api_secret, user_id)
        self.smart_api = None
        self.totp_secret = None  # For TOTP-based login

    @property
    def name(self) -> str:
        return "angel"

    def set_totp_secret(self, totp_secret: str):
        """Set TOTP secret for automated login"""
        self.totp_secret = totp_secret

    def login(self) -> bool:
        """Login to Angel One SmartAPI"""
        try:
            from SmartApi import SmartConnect
            import pyotp

            self.smart_api = SmartConnect(api_key=self.api_key)

            # Generate TOTP if secret is provided
            totp = None
            if self.totp_secret:
                totp = pyotp.TOTP(self.totp_secret).now()
            else:
                totp = input("Enter TOTP: ")

            # Login
            data = self.smart_api.generateSession(
                clientCode=self.user_id,
                password=self.api_secret,
                totp=totp
            )

            if data["status"]:
                self.access_token = data["data"]["jwtToken"]
                refresh_token = data["data"]["refreshToken"]

                # Get profile to verify
                profile = self.smart_api.getProfile(refresh_token)
                logger.info(f"Angel One login successful for {profile['data']['name']}")

                self.is_authenticated = True
                return True
            else:
                logger.error(f"Angel One login failed: {data['message']}")
                return False

        except Exception as e:
            logger.error(f"Angel One login failed: {e}")
            return False

    def _convert_exchange(self, exchange: str) -> str:
        """Convert exchange to Angel format"""
        mapping = {
            "BSE": "BSE",
            "NSE": "NSE",
            "NFO": "NFO",
            "BFO": "BFO"
        }
        return mapping.get(exchange, exchange)

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert order type to Angel format"""
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.SL: "STOPLOSS_LIMIT",
            OrderType.SL_M: "STOPLOSS_MARKET"
        }
        return mapping.get(order_type, "MARKET")

    def _convert_product(self, product: ProductType) -> str:
        """Convert product type to Angel format"""
        mapping = {
            ProductType.NRML: "CARRYFORWARD",
            ProductType.MIS: "INTRADAY",
            ProductType.CNC: "DELIVERY"
        }
        return mapping.get(product, "CARRYFORWARD")

    def _get_token(self, symbol: str, exchange: str) -> str:
        """Get instrument token for a symbol"""
        # Angel One requires token lookup from their instrument master
        # This is a simplified version - in production, load from CSV
        try:
            # Try to get from LTP which returns token
            ltp_data = self.smart_api.ltpData(
                exchange=self._convert_exchange(exchange),
                tradingsymbol=symbol,
                symboltoken=""
            )
            return ltp_data["data"]["symboltoken"]
        except:
            logger.warning(f"Could not find token for {symbol}, using symbol as token")
            return symbol

    def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Get current quote for a symbol"""
        try:
            exchange = self._convert_exchange(exchange)
            token = self._get_token(symbol, exchange)

            data = self.smart_api.ltpData(
                exchange=exchange,
                tradingsymbol=symbol,
                symboltoken=token
            )

            ltp = data["data"]["ltp"]

            return Quote(
                symbol=symbol,
                last_price=ltp,
                bid=ltp,  # Angel LTP doesn't give depth
                ask=ltp,
                volume=0,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise

    def get_option_chain(self, symbol: str, expiry: str) -> dict:
        """
        Get option chain for an index
        Angel One provides option chain via separate API
        """
        try:
            # Angel One option chain endpoint
            # Map symbol to their format
            symbol_map = {
                "NIFTY": "NIFTY",
                "BANKNIFTY": "BANKNIFTY",
                "SENSEX": "SENSEX",
                "BANKEX": "BANKEX"
            }

            chain_data = self.smart_api.getOptionChain({
                "name": symbol_map.get(symbol, symbol),
                "expiryDate": expiry
            })

            chain = {"calls": [], "puts": []}

            if chain_data["status"] and chain_data["data"]:
                for item in chain_data["data"]:
                    call_data = {
                        "strike": item["strikePrice"],
                        "symbol": item["CEsymbol"],
                        "last_price": item["CEltp"],
                        "bid": item.get("CEbidPrice", 0),
                        "ask": item.get("CEaskPrice", 0),
                        "volume": item.get("CEvolume", 0),
                        "oi": item.get("CEopenInterest", 0),
                        "oi_change": item.get("CEoiChange", 0)
                    }
                    put_data = {
                        "strike": item["strikePrice"],
                        "symbol": item["PEsymbol"],
                        "last_price": item["PEltp"],
                        "bid": item.get("PEbidPrice", 0),
                        "ask": item.get("PEaskPrice", 0),
                        "volume": item.get("PEvolume", 0),
                        "oi": item.get("PEopenInterest", 0),
                        "oi_change": item.get("PEoiChange", 0)
                    }
                    chain["calls"].append(call_data)
                    chain["puts"].append(put_data)

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
            token = self._get_token(symbol, exchange)

            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": side.value,
                "exchange": self._convert_exchange(exchange),
                "ordertype": self._convert_order_type(order_type),
                "producttype": self._convert_product(product),
                "duration": "DAY",
                "quantity": str(quantity)
            }

            if order_type == OrderType.LIMIT:
                order_params["price"] = str(price)
            elif order_type in [OrderType.SL, OrderType.SL_M]:
                order_params["triggerprice"] = str(trigger_price)
                if order_type == OrderType.SL:
                    order_params["price"] = str(price)

            response = self.smart_api.placeOrder(order_params)

            if response["status"]:
                order_id = response["data"]["orderid"]
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
            else:
                raise Exception(response["message"])

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
            # Get original order details first
            original = self.get_order_status(order_id)

            modify_params = {
                "variety": "NORMAL",
                "orderid": order_id,
                "tradingsymbol": original.symbol,
                "symboltoken": self._get_token(original.symbol, original.exchange),
                "exchange": self._convert_exchange(original.exchange),
                "ordertype": self._convert_order_type(original.order_type),
                "producttype": self._convert_product(original.product),
                "duration": "DAY",
                "quantity": str(quantity if quantity else original.quantity)
            }

            if price is not None:
                modify_params["price"] = str(price)
            if trigger_price is not None:
                modify_params["triggerprice"] = str(trigger_price)

            response = self.smart_api.modifyOrder(modify_params)

            if response["status"]:
                logger.info(f"Order modified: {order_id}")
                return self.get_order_status(order_id)
            else:
                raise Exception(response["message"])

        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            response = self.smart_api.cancelOrder(order_id, "NORMAL")

            if response["status"]:
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Cancel failed: {response['message']}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        try:
            orders = self.smart_api.orderBook()

            if orders["status"] and orders["data"]:
                for o in orders["data"]:
                    if str(o["orderid"]) == str(order_id):
                        return Order(
                            order_id=str(o["orderid"]),
                            symbol=o["tradingsymbol"],
                            exchange=o["exchange"],
                            side=OrderSide(o["transactiontype"]),
                            order_type=self._reverse_order_type(o["ordertype"]),
                            quantity=int(o["quantity"]),
                            price=float(o.get("price", 0)),
                            trigger_price=float(o.get("triggerprice", 0)),
                            product=self._reverse_product(o["producttype"]),
                            status=o["status"],
                            filled_quantity=int(o.get("filledshares", 0)),
                            average_price=float(o.get("averageprice", 0)),
                            timestamp=datetime.now()
                        )

            raise ValueError(f"Order {order_id} not found")

        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            raise

    def _reverse_order_type(self, angel_type: str) -> OrderType:
        """Convert Angel order type back to our format"""
        mapping = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOPLOSS_LIMIT": OrderType.SL,
            "STOPLOSS_MARKET": OrderType.SL_M
        }
        return mapping.get(angel_type, OrderType.MARKET)

    def _reverse_product(self, angel_product: str) -> ProductType:
        """Convert Angel product type back to our format"""
        mapping = {
            "CARRYFORWARD": ProductType.NRML,
            "INTRADAY": ProductType.MIS,
            "DELIVERY": ProductType.CNC
        }
        return mapping.get(angel_product, ProductType.NRML)

    def get_positions(self) -> list[Position]:
        """Get all open positions"""
        try:
            response = self.smart_api.position()
            result = []

            if response["status"] and response["data"]:
                for p in response["data"]:
                    qty = int(p.get("netqty", 0))
                    if qty != 0:
                        result.append(Position(
                            symbol=p["tradingsymbol"],
                            exchange=p["exchange"],
                            quantity=qty,
                            average_price=float(p.get("averageprice", 0)),
                            last_price=float(p.get("ltp", 0)),
                            pnl=float(p.get("pnl", 0)),
                            product=self._reverse_product(p["producttype"])
                        ))

            return result

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    def get_margins(self) -> dict:
        """Get available margins"""
        try:
            response = self.smart_api.rmsLimit()

            if response["status"] and response["data"]:
                data = response["data"]
                return {
                    "available": float(data.get("availablecash", 0)),
                    "used": float(data.get("utiliseddebits", 0)),
                    "total": float(data.get("net", 0))
                }

            return {"available": 0, "used": 0, "total": 0}

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
            token = self._get_token(symbol, exchange)

            # Map interval to Angel format
            interval_map = {
                "1minute": "ONE_MINUTE",
                "5minute": "FIVE_MINUTE",
                "15minute": "FIFTEEN_MINUTE",
                "day": "ONE_DAY"
            }

            params = {
                "exchange": self._convert_exchange(exchange),
                "symboltoken": token,
                "interval": interval_map.get(interval, "ONE_DAY"),
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M")
            }

            response = self.smart_api.getCandleData(params)

            if response["status"] and response["data"]:
                return [
                    {
                        "timestamp": d[0],
                        "open": d[1],
                        "high": d[2],
                        "low": d[3],
                        "close": d[4],
                        "volume": d[5]
                    }
                    for d in response["data"]
                ]

            return []

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            raise
