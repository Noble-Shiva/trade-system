"""
Logging Utility
Provides centralized logging for the trading system
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class TradingLogger:
    """Centralized logging for trading system"""

    def __init__(self, name="TradingSystem", log_dir=None, log_level=logging.INFO):
        """
        Initialize logger

        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Logging level
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Avoid adding handlers multiple times
        if not self.logger.handlers:
            # Log directory
            if log_dir is None:
                log_dir = Path(__file__).parent.parent.parent / 'logs'
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Create formatters
            file_formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )

            # File handler - daily log file
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = self.log_dir / f"trading_{today}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(console_formatter)

            # Add handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)

    def info(self, message):
        """Log info message"""
        self.logger.info(message)

    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message):
        """Log error message"""
        self.logger.error(message)

    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)

    def trade(self, message):
        """Log trade-specific message"""
        self.logger.info(f"[TRADE] {message}")

    def signal(self, message):
        """Log signal-specific message"""
        self.logger.info(f"[SIGNAL] {message}")

    def risk(self, message):
        """Log risk-specific message"""
        self.logger.warning(f"[RISK] {message}")


# Create global logger instance
logger = TradingLogger()


if __name__ == "__main__":
    # Test logger
    print("Testing Logger...")
    print("-" * 60)

    log = TradingLogger("TestLogger")

    log.info("System started")
    log.debug("Debug message")
    log.warning("Warning message")
    log.trade("NIFTY 21500 CE bought @ ₹147")
    log.signal("Bullish momentum detected")
    log.risk("Daily loss limit: 50% consumed")

    print("\n✅ Logger working successfully!")
    print(f"Log file created in: {log.log_dir}")
