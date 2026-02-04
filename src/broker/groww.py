"""
Groww Trade API Broker Implementation
"""

from datetime import datetime
from typing import Optional
from loguru import logger

from .base import (
    BrokerBase, Order, Position, Quote,
    OrderType, OrderSide, ProductType, Exchange
)


class GrowwBroker(BrokerBase):
    """Groww Trade API implementation"""

    def __init__(self, api_key: str, api_secret: str, user_id: str = None):
        super().__init__(api_key, api_secret, user_id)
        self.groww = None
        self.totp_secret = None  # For TOTP-based login

    @property
    def name(self) -> str:
        return "groww"

    def set_totp_secret(self, totp_secret: str):
        """Set TOTP secret for automated login"""
        self.totp_secret = totp_secret

    def login(self) -> bool:
        """
        Login to Groww Trade API

        Supports two methods:
        1. API Key + Secret (requires daily approval on Groww Cloud)
        2. API Key + TOTP (no expiry)
        """
        try:
            from growwapi import GrowwAPI
            import pyotp

            # Try TOTP login first (preferred for automation)
            if self.totp_secret:
                totp = pyotp.TOTP(self.totp_secret).now()
                self.access_token = GrowwAPI.get_access_token(
                    api_key=self.api_key,
                    totp=totp
                )
            else:
                # Fallback to API Key + Secret
                self.access_token = GrowwAPI.get_access_token(
                    api_key=self.api_key,
                    secret=self.api_secret
                )

            # Initialize Groww API with access token
            self.groww = GrowwAPI(self.access_token)

            self.is_authenticated = True
            logger.info("Groww login successful")
            return True

        except Exception as e:
            logger.error(f"Groww login failed: {e}")
            return False

    def _convert_exchange(self, exchange: str) -> str:
        """Convert exchange to Groww format"""
        # Groww uses same format
        mapping = {
            "BSE": self.groww.EXCHANGE_BSE,
            "NSE": self.groww.EXCHANGE_NSE,
            "NFO": self.groww.EXCHANGE_NSE,  # F&O on NSE
            "BFO": self.groww.EXCHANGE_BSE   # F&O on BSE
        }
        return mapping.get(exchange, self.groww.EXCHANGE_NSE)

    def _convert_segment(self, exchange: str) -> str:
        """Convert exchange to Groww segment"""
        segment_mapping = {
            "BSE": self.groww.SEGMENT_CASH,
            "NSE": self.groww.SEGMENT_CASH,
            "NFO": self.groww.SEGMENT_FNO,
            "BFO": self.groww.SEGMENT_FNO
        }
        return segment_mapping.get(exchange, self.groww.SEGMENT_CASH)

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert order type to Groww format"""
        mapping = {
            OrderType.MARKET: self.groww.ORDER_TYPE_MARKET,
            OrderType.LIMIT: self.groww.ORDER_TYPE_LIMIT,
            OrderType.SL: self.groww.ORDER_TYPE_STOP_LOSS,
            OrderType.SL_M: self.groww.ORDER_TYPE_STOP_LOSS_MARKET
        }
        return mapping.get(order_type, self.groww.ORDER_TYPE_MARKET)

    def _convert_product(self, product: ProductType) -> str:
        """Convert product type to Groww format"""
        mapping = {
            ProductType.NRML: self.groww.PRODUCT_NRML,
            ProductType.MIS: self.groww.PRODUCT_MIS,
            ProductType.CNC: self.groww.PRODUCT_CNC
        }
        return mapping.get(product, self.groww.PRODUCT_NRML)

    def _convert_transaction_type(self, side: OrderSide) -> str:
        """Convert order side to Groww transaction type"""
        if side == OrderSide.BUY:
            return self.groww.TRANSACTION_TYPE_BUY
        else:
            return self.groww.TRANSACTION_TYPE_SELL

    def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Get current quote for a symbol"""
        try:
            groww_exchange = self._convert_exchange(exchange)
            segment = self._convert_segment(exchange)

            response = self.groww.get_quote(
                exchange=groww_exchange,
                segment=segment,
                trading_symbol=symbol
            )

            data = response.get("data", {})

            return Quote(
                symbol=symbol,
                last_price=data.get("ltp", 0),
                bid=data.get("bid_price", 0),
                ask=data.get("ask_price", 0),
                volume=data.get("volume", 0),
                open=data.get("ohlc", {}).get("open", 0),
                high=data.get("ohlc", {}).get("high", 0),
                low=data.get("ohlc", {}).get("low", 0),
                close=data.get("ohlc", {}).get("close", 0),
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise

    def get_option_chain(self, symbol: str, expiry: str) -> dict:
        """
        Get option chain for an index

        Args:
            symbol: NIFTY, BANKNIFTY, etc.
            expiry: Expiry date (YYYY-MM-DD)
        """
        try:
            response = self.groww.get_option_chain(
                exchange=self.groww.EXCHANGE_NSE,
                underlying=symbol,
                expiry_date=expiry
            )

            data = response.get("data", {})
            chain = {"calls": [], "puts": []}

            for strike_data in data.get("option_chain", []):
                strike = strike_data.get("strike_price")

                # Call data
                ce = strike_data.get("CE", {})
                if ce:
                    chain["calls"].append({
                        "strike": strike,
                        "symbol": ce.get("trading_symbol", ""),
                        "last_price": ce.get("ltp", 0),
                        "bid": ce.get("bid_price", 0),
                        "ask": ce.get("ask_price", 0),
                        "volume": ce.get("volume", 0),
                        "oi": ce.get("open_interest", 0),
                        "oi_change": ce.get("oi_change", 0),
                        "iv": ce.get("implied_volatility", 0),
                        "delta": ce.get("delta", 0),
                        "gamma": ce.get("gamma", 0),
                        "theta": ce.get("theta", 0),
                        "vega": ce.get("vega", 0)
                    })

                # Put data
                pe = strike_data.get("PE", {})
                if pe:
                    chain["puts"].append({
                        "strike": strike,
                        "symbol": pe.get("trading_symbol", ""),
                        "last_price": pe.get("ltp", 0),
                        "bid": pe.get("bid_price", 0),
                        "ask": pe.get("ask_price", 0),
                        "volume": pe.get("volume", 0),
                        "oi": pe.get("open_interest", 0),
                        "oi_change": pe.get("oi_change", 0),
                        "iv": pe.get("implied_volatility", 0),
                        "delta": pe.get("delta", 0),
                        "gamma": pe.get("gamma", 0),
                        "theta": pe.get("theta", 0),
                        "vega": pe.get("vega", 0)
                    })

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
            order_params = {
                "trading_symbol": symbol,
                "quantity": quantity,
                "validity": self.groww.VALIDITY_DAY,
                "exchange": self._convert_exchange(exchange),
                "segment": self._convert_segment(exchange),
                "product": self._convert_product(product),
                "order_type": self._convert_order_type(order_type),
                "transaction_type": self._convert_transaction_type(side)
            }

            # Add price for limit orders
            if order_type == OrderType.LIMIT:
                order_params["price"] = price

            # Add trigger price for stop-loss orders
            if order_type in [OrderType.SL, OrderType.SL_M]:
                order_params["trigger_price"] = trigger_price
                if order_type == OrderType.SL:
                    order_params["price"] = price

            response = self.groww.place_order(**order_params)

            if response.get("success"):
                data = response.get("data", {})
                order_id = data.get("groww_order_id", "")

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
                    status=data.get("order_status", "PENDING")
                )
            else:
                raise Exception(response.get("message", "Order placement failed"))

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
            # Get original order to know segment
            original = self.get_order_status(order_id)

            modify_params = {
                "groww_order_id": order_id,
                "segment": self._convert_segment(original.exchange),
                "order_type": self._convert_order_type(original.order_type)
            }

            if quantity is not None:
                modify_params["quantity"] = quantity
            if price is not None:
                modify_params["price"] = price
            if trigger_price is not None:
                modify_params["trigger_price"] = trigger_price

            response = self.groww.modify_order(**modify_params)

            if response.get("success"):
                logger.info(f"Order modified: {order_id}")
                return self.get_order_status(order_id)
            else:
                raise Exception(response.get("message", "Order modification failed"))

        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            # Get order to know segment
            order = self.get_order_status(order_id)

            response = self.groww.cancel_order(
                segment=self._convert_segment(order.exchange),
                groww_order_id=order_id
            )

            if response.get("success"):
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Cancel failed: {response.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        try:
            # Get order list and find by ID
            response = self.groww.get_order_list()

            if response.get("success"):
                orders = response.get("data", {}).get("orders", [])

                for o in orders:
                    if str(o.get("groww_order_id")) == str(order_id):
                        return Order(
                            order_id=str(o.get("groww_order_id")),
                            symbol=o.get("trading_symbol", ""),
                            exchange=self._reverse_exchange(o.get("exchange")),
                            side=OrderSide.BUY if o.get("transaction_type") == "BUY" else OrderSide.SELL,
                            order_type=self._reverse_order_type(o.get("order_type")),
                            quantity=int(o.get("quantity", 0)),
                            price=float(o.get("price", 0)),
                            trigger_price=float(o.get("trigger_price", 0)),
                            product=self._reverse_product(o.get("product")),
                            status=o.get("order_status", ""),
                            filled_quantity=int(o.get("filled_quantity", 0)),
                            average_price=float(o.get("average_price", 0)),
                            timestamp=datetime.now()
                        )

            raise ValueError(f"Order {order_id} not found")

        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            raise

    def _reverse_exchange(self, groww_exchange: str) -> str:
        """Convert Groww exchange back to our format"""
        if groww_exchange == "NSE":
            return "NSE"
        elif groww_exchange == "BSE":
            return "BSE"
        return "NSE"

    def _reverse_order_type(self, groww_type: str) -> OrderType:
        """Convert Groww order type back"""
        mapping = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP_LOSS": OrderType.SL,
            "STOP_LOSS_MARKET": OrderType.SL_M
        }
        return mapping.get(groww_type, OrderType.MARKET)

    def _reverse_product(self, groww_product: str) -> ProductType:
        """Convert Groww product back"""
        mapping = {
            "NRML": ProductType.NRML,
            "MIS": ProductType.MIS,
            "CNC": ProductType.CNC
        }
        return mapping.get(groww_product, ProductType.NRML)

    def get_positions(self) -> list[Position]:
        """Get all open positions"""
        try:
            response = self.groww.get_positions_for_user()

            result = []

            if response.get("success"):
                positions = response.get("data", {}).get("positions", [])

                for p in positions:
                    qty = int(p.get("net_quantity", 0))
                    if qty != 0:
                        result.append(Position(
                            symbol=p.get("trading_symbol", ""),
                            exchange=self._reverse_exchange(p.get("exchange", "")),
                            quantity=qty,
                            average_price=float(p.get("average_price", 0)),
                            last_price=float(p.get("ltp", 0)),
                            pnl=float(p.get("realised_pnl", 0)),
                            product=self._reverse_product(p.get("product", ""))
                        ))

            return result

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    def get_margins(self) -> dict:
        """Get available margins"""
        try:
            response = self.groww.get_available_margin_details()

            if response.get("success"):
                data = response.get("data", {})

                return {
                    "available": float(data.get("available_cash", 0)),
                    "used": float(data.get("total_margin_used", 0)),
                    "total": float(data.get("available_cash", 0)) + float(data.get("total_margin_used", 0))
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
        """
        Get historical OHLCV data

        Note: Groww API documentation doesn't show historical data endpoint.
        This is a placeholder - you may need to use alternative sources.
        """
        logger.warning("Historical data not directly available from Groww API")
        logger.info("Consider using NSEPython or Yahoo Finance for historical data")

        # Return empty list as Groww doesn't provide historical data API
        return []
