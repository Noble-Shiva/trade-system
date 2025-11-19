#!/usr/bin/env python3
"""
Main entry point for the trading system
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from dotenv import load_dotenv

from src.engine import TradingOrchestrator


def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/trading_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level=log_level
    )


def main():
    parser = argparse.ArgumentParser(description="BSE F&O Automated Trading System")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Run in paper trading mode"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging(args.log_level)

    logger.info("=" * 50)
    logger.info("BSE F&O Automated Trading System")
    logger.info("=" * 50)

    if args.paper:
        logger.info("Running in PAPER TRADING mode")

    try:
        # Initialize and start trading
        orchestrator = TradingOrchestrator(args.config)
        orchestrator.start()

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
