"""
Angel One API Helper
Helper functions for Angel One Smart API integration
"""

import os
from SmartApi import SmartConnect
from src.utils.logger import TradingLogger

logger = TradingLogger("AngelOneHelper")


class AngelOneAPI:
    """Angel One Smart API wrapper"""

    def __init__(self, api_key=None, client_id=None, password=None, totp_secret=None):
        """
        Initialize Angel One API

        Args:
            api_key: Angel One API key
            client_id: Angel One client ID
            password: Angel One password
            totp_secret: TOTP secret for 2FA
        """
        # Get credentials from environment if not provided
        self.api_key = api_key or os.getenv('ANGEL_API_KEY')
        self.client_id = client_id or os.getenv('ANGEL_CLIENT_ID')
        self.password = password or os.getenv('ANGEL_PASSWORD')
        self.totp_secret = totp_secret or os.getenv('ANGEL_TOTP_SECRET')

        # Initialize SmartConnect
        self.smart_api = None
        self.session_token = None
        self.feed_token = None

    def connect(self):
        """Connect to Angel One API"""
        try:
            logger.info("Connecting to Angel One API...")

            if not all([self.api_key, self.client_id, self.password]):
                raise ValueError("Missing Angel One credentials. Please set ANGEL_API_KEY, ANGEL_CLIENT_ID, and ANGEL_PASSWORD in .env file")

            # Create SmartConnect instance
            self.smart_api = SmartConnect(api_key=self.api_key)

            # Generate session
            # Note: For TOTP, you need pyotp library
            # For now, we'll use password-based login
            data = self.smart_api.generateSession(self.client_id, self.password)

            if data['status']:
                self.session_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                logger.info("✅ Connected to Angel One successfully!")
                return True
            else:
                logger.error(f"Failed to connect: {data.get('message', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Angel One: {e}")
            return False

    def get_profile(self):
        """Get user profile"""
        if not self.smart_api:
            logger.error("Not connected to Angel One API")
            return None

        try:
            profile = self.smart_api.getProfile(self.session_token)
            return profile
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return None

    def get_ltp(self, symbol, exchange="NSE", token=None):
        """
        Get Last Traded Price (LTP)

        Args:
            symbol: Trading symbol (e.g., "NIFTY")
            exchange: Exchange (NSE, NFO, BSE)
            token: Instrument token

        Returns:
            LTP or None
        """
        if not self.smart_api:
            logger.error("Not connected to Angel One API")
            return None

        try:
            # Note: You'll need to get the token from instrument master
            # For now, this is a placeholder
            logger.info(f"Fetching LTP for {symbol} on {exchange}")
            return None
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            return None

    def place_order(self, symbol, quantity, order_type="MARKET", transaction_type="BUY",
                   product_type="INTRADAY", price=0, trigger_price=0):
        """
        Place an order

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, SL-M
            transaction_type: BUY or SELL
            product_type: INTRADAY, DELIVERY, CARRYFORWARD
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)

        Returns:
            Order response
        """
        if not self.smart_api:
            logger.error("Not connected to Angel One API")
            return None

        try:
            logger.info(f"Placing {transaction_type} order for {symbol}, Qty: {quantity}")

            # Note: This is a simplified version
            # In production, you'll need proper symbol token mapping
            # and order parameters validation

            return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def disconnect(self):
        """Disconnect from Angel One API"""
        if self.smart_api:
            try:
                self.smart_api.terminateSession(self.client_id)
                logger.info("Disconnected from Angel One API")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")


if __name__ == "__main__":
    print("Angel One API Helper")
    print("-" * 60)
    print("\nTo test connection:")
    print("1. Open Angel One account")
    print("2. Apply for Smart API")
    print("3. Update .env file with credentials:")
    print("   - ANGEL_API_KEY=your_api_key")
    print("   - ANGEL_CLIENT_ID=your_client_id")
    print("   - ANGEL_PASSWORD=your_password")
    print("\nThen uncomment and run the test code below:")
    print("-" * 60)

    # Uncomment to test (after setting up credentials)
    # api = AngelOneAPI()
    # if api.connect():
    #     profile = api.get_profile()
    #     print(f"Profile: {profile}")
    #     api.disconnect()
