"""
Broker Factory - Create broker instances from configuration
"""

from .base import BrokerBase
from .zerodha import ZerodhaBroker
from .angel import AngelOneBroker
from .groww import GrowwBroker


class BrokerFactory:
    """Factory for creating broker instances"""

    _brokers = {
        "zerodha": ZerodhaBroker,
        "angel": AngelOneBroker,
        "groww": GrowwBroker,
        # Add more brokers here
        # "fyers": FyersBroker,
        # "upstox": UpstoxBroker,
    }

    @classmethod
    def create(cls, broker_name: str, api_key: str, api_secret: str, user_id: str = None) -> BrokerBase:
        """
        Create a broker instance

        Args:
            broker_name: Name of broker (zerodha, angel, etc.)
            api_key: API key/client ID
            api_secret: API secret/password
            user_id: User ID (required for some brokers)

        Returns:
            BrokerBase instance

        Example:
            broker = BrokerFactory.create(
                "zerodha",
                api_key="your_api_key",
                api_secret="your_api_secret"
            )
        """
        broker_name = broker_name.lower()

        if broker_name not in cls._brokers:
            available = ", ".join(cls._brokers.keys())
            raise ValueError(f"Unknown broker: {broker_name}. Available: {available}")

        broker_class = cls._brokers[broker_name]
        return broker_class(api_key, api_secret, user_id)

    @classmethod
    def available_brokers(cls) -> list[str]:
        """Get list of available broker names"""
        return list(cls._brokers.keys())

    @classmethod
    def register(cls, name: str, broker_class: type):
        """Register a new broker implementation"""
        if not issubclass(broker_class, BrokerBase):
            raise TypeError(f"{broker_class} must be a subclass of BrokerBase")
        cls._brokers[name.lower()] = broker_class
