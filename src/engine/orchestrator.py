"""
Trading Orchestrator - Main engine that coordinates all components
"""

import time
import yaml
from datetime import datetime, time as dtime
from pathlib import Path
from loguru import logger

from ..broker import BrokerFactory, OrderType, OrderSide, ProductType
from ..data import DataFetcher, OptionChainAnalyzer
from ..strategies import IronCondorStrategy, BullPutSpreadStrategy, BearCallSpreadStrategy
from ..risk import RiskManager, DynamicStopLoss
from ..notifications import TelegramNotifier


class TradingOrchestrator:
    """
    Main trading engine that:
    1. Initializes at market open
    2. Analyzes market for opportunities
    3. Executes trades
    4. Monitors and manages positions
    5. Updates stop-losses dynamically
    6. Sends notifications
    """

    def __init__(self, config_path: str = "config/settings.yaml", paper_mode: bool = False):
        # Load configuration
        self.config = self._load_config(config_path)
        self.paper_mode = paper_mode

        # Initialize components
        self.broker = None
        self.data_fetcher = None
        self.strategies = []
        self.risk_manager = None
        self.stop_loss_manager = None
        self.notifier = None

        # State
        self.positions = []
        self.orders = []
        self.daily_trades = []
        self.running = False

        self._initialize_components()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        import os
        for key, value in config.get("broker", {}).items():
            if isinstance(value, str) and value.startswith("${"):
                env_var = value[2:-1]
                config["broker"][key] = os.getenv(env_var, "")

        return config

    def _initialize_components(self):
        """Initialize all trading components"""
        # Broker
        broker_config = self.config.get("broker", {})
        
        if self.paper_mode:
            # Use paper broker for simulation
            capital_config = self.config.get("capital", {})
            self.broker = BrokerFactory.create(
                broker_name="paper",
                initial_capital=capital_config.get("initial", 100000)
            )
        else:
            # Use real broker
            self.broker = BrokerFactory.create(
                broker_name=broker_config.get("name", "zerodha"),
                api_key=broker_config.get("api_key", ""),
                api_secret=broker_config.get("api_secret", ""),
                user_id=broker_config.get("user_id", "")
            )

        # Data fetcher
        self.data_fetcher = DataFetcher(self.broker)

        # Strategies
        strategy_config = self.config.get("strategies", {})
        if strategy_config.get("iron_condor", {}).get("enabled", True):
            self.strategies.append(IronCondorStrategy(strategy_config.get("iron_condor", {})))
        if strategy_config.get("bull_put_spread", {}).get("enabled", True):
            self.strategies.append(BullPutSpreadStrategy(strategy_config.get("bull_put_spread", {})))
        if strategy_config.get("bear_call_spread", {}).get("enabled", True):
            self.strategies.append(BearCallSpreadStrategy(strategy_config.get("bear_call_spread", {})))

        # Risk management
        self.risk_manager = RiskManager(self.config.get("risk", {}))
        self.stop_loss_manager = DynamicStopLoss(self.config.get("stop_loss", {}))

        # Notifications
        telegram_config = self.config.get("notifications", {}).get("telegram", {})
        self.notifier = TelegramNotifier(
            bot_token=telegram_config.get("bot_token", ""),
            chat_id=telegram_config.get("chat_id", "")
        )

        logger.info("Trading components initialized")

    def start(self):
        """Start the trading system"""
        logger.info("Starting trading system...")

        # Login to broker
        if not self.broker.login():
            logger.error("Broker login failed. Exiting.")
            return

        self.running = True
        self.notifier.notify_system_start()

        # Main trading loop
        try:
            while self.running:
                current_time = datetime.now().time()

                # Check if within trading hours
                market_start = dtime(9, 15)
                market_end = dtime(15, 30)
                no_new_trades = dtime(14, 30)

                if current_time < market_start:
                    logger.info("Waiting for market open...")
                    time.sleep(60)
                    continue

                if current_time > market_end:
                    logger.info("Market closed for the day")
                    self._end_of_day()
                    break

                # Get capital
                margins = self.broker.get_margins()
                capital = margins.get("available", 0)

                # Check if we can trade
                can_trade, reason = self.risk_manager.can_trade(capital)

                if can_trade and current_time < no_new_trades:
                    # Look for new opportunities
                    self._scan_for_trades(capital)

                # Monitor existing positions
                self._monitor_positions()

                # Update stop-losses
                self._update_stop_losses()

                # Sleep before next iteration
                time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.notifier.notify_alert("System Error", str(e), "ERROR")
        finally:
            self.stop()

    def stop(self):
        """Stop the trading system"""
        self.running = False
        self._end_of_day()
        self.notifier.notify_system_stop()
        logger.info("Trading system stopped")

    def _scan_for_trades(self, capital: float):
        """Scan market for trading opportunities"""
        symbols = self.config.get("market", {}).get("instruments", ["NIFTY"])

        for symbol in symbols:
            try:
                # Get market data
                spot_price = self.data_fetcher.get_index_price(symbol)
                option_chain = self.data_fetcher.get_option_chain(symbol)
                vix = self.data_fetcher.get_vix()

                market_data = {
                    "symbol": symbol,
                    "spot_price": spot_price,
                    "option_chain": option_chain.get("chain_data", {}),
                    "vix": vix
                }

                # Check each strategy
                for strategy in self.strategies:
                    if not strategy.should_trade_today(market_data):
                        continue

                    if strategy.min_capital_required > capital:
                        continue

                    # Get signals
                    signals = strategy.analyze(market_data)

                    for signal in signals:
                        self._execute_signal(signal, capital)

            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

    def _execute_signal(self, signal, capital: float):
        """Execute a trading signal"""
        try:
            # Place order
            exchange = "NFO"  # Default to NSE F&O
            side = OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL

            order = self.broker.place_order(
                symbol=signal.symbol,
                exchange=exchange,
                side=side,
                quantity=signal.quantity,
                order_type=OrderType.MARKET,
                product=ProductType.NRML
            )

            self.orders.append(order)
            self.risk_manager.add_position()

            # Track position
            position = {
                "symbol": signal.symbol,
                "order_id": order.order_id,
                "entry_price": signal.price,
                "quantity": signal.quantity,
                "type": signal.action,
                "stop_loss": signal.stop_loss,
                "target": signal.target,
                "strategy": signal.metadata.get("strategy", ""),
                "entry_time": datetime.now()
            }
            self.positions.append(position)
            self.daily_trades.append(position)

            # Notify
            self.notifier.notify_trade_entry(
                symbol=signal.symbol,
                action=signal.action,
                quantity=signal.quantity,
                price=signal.price,
                stop_loss=signal.stop_loss,
                strategy=signal.metadata.get("strategy", "")
            )

            logger.info(f"Executed: {signal.action} {signal.quantity} {signal.symbol} @ {signal.price}")

        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
            self.notifier.notify_alert("Order Failed", str(e), "ERROR")

    def _monitor_positions(self):
        """Monitor open positions for exit conditions"""
        for position in self.positions[:]:  # Copy list to allow removal
            try:
                # Get current price
                quote = self.broker.get_quote(position["symbol"], "NFO")
                current_price = quote.last_price

                # Check stop loss
                if self.stop_loss_manager.should_exit(
                    current_price,
                    position["stop_loss"],
                    "LONG" if position["type"] == "BUY" else "SHORT"
                ):
                    self._exit_position(position, current_price, "Stop loss hit")
                    continue

                # Check target
                if position["target"] > 0:
                    if position["type"] == "SELL":
                        # For sold options, target when price decreases
                        if current_price <= position["target"]:
                            self._exit_position(position, current_price, "Target reached")

            except Exception as e:
                logger.error(f"Error monitoring {position['symbol']}: {e}")

    def _update_stop_losses(self):
        """Update dynamic stop losses for all positions"""
        for position in self.positions:
            try:
                quote = self.broker.get_quote(position["symbol"], "NFO")
                current_price = quote.last_price

                new_sl = self.stop_loss_manager.update_trailing_sl(
                    entry_price=position["entry_price"],
                    current_price=current_price,
                    current_sl=position["stop_loss"],
                    position_type="LONG" if position["type"] == "BUY" else "SHORT"
                )

                if new_sl.price != position["stop_loss"]:
                    old_sl = position["stop_loss"]
                    position["stop_loss"] = new_sl.price

                    self.notifier.notify_stop_loss_update(
                        symbol=position["symbol"],
                        old_sl=old_sl,
                        new_sl=new_sl.price,
                        reason=new_sl.reason
                    )

            except Exception as e:
                logger.error(f"Error updating SL for {position['symbol']}: {e}")

    def _exit_position(self, position: dict, exit_price: float, reason: str):
        """Exit a position"""
        try:
            # Place exit order
            side = OrderSide.SELL if position["type"] == "BUY" else OrderSide.BUY

            order = self.broker.place_order(
                symbol=position["symbol"],
                exchange="NFO",
                side=side,
                quantity=position["quantity"],
                order_type=OrderType.MARKET,
                product=ProductType.NRML
            )

            # Calculate P&L
            if position["type"] == "BUY":
                pnl = (exit_price - position["entry_price"]) * position["quantity"]
            else:
                pnl = (position["entry_price"] - exit_price) * position["quantity"]

            # Update risk manager
            margins = self.broker.get_margins()
            self.risk_manager.update_pnl(pnl, margins.get("available", 0))
            self.risk_manager.remove_position()

            # Remove from positions
            self.positions.remove(position)

            # Notify
            self.notifier.notify_trade_exit(
                symbol=position["symbol"],
                action=side.value,
                quantity=position["quantity"],
                entry_price=position["entry_price"],
                exit_price=exit_price,
                pnl=pnl,
                reason=reason
            )

            logger.info(f"Exited {position['symbol']} - P&L: ₹{pnl:.2f} - {reason}")

        except Exception as e:
            logger.error(f"Failed to exit position: {e}")

    def _end_of_day(self):
        """End of day procedures"""
        # Square off all positions
        if self.positions:
            logger.info("Squaring off all positions...")
            for position in self.positions[:]:
                try:
                    quote = self.broker.get_quote(position["symbol"], "NFO")
                    self._exit_position(position, quote.last_price, "End of day")
                except Exception as e:
                    logger.error(f"Failed to square off {position['symbol']}: {e}")

        # Send daily summary
        winning = sum(1 for t in self.daily_trades if t.get("pnl", 0) > 0)
        total_pnl = sum(t.get("pnl", 0) for t in self.daily_trades)

        margins = self.broker.get_margins() if self.broker.is_authenticated else {"available": 0}

        self.notifier.notify_daily_summary(
            total_trades=len(self.daily_trades),
            winning_trades=winning,
            daily_pnl=total_pnl,
            capital=margins.get("available", 0)
        )

        logger.info(f"Day ended - Total trades: {len(self.daily_trades)}, P&L: ₹{total_pnl:.2f}")
