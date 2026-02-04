"""
Telegram Notifications
"""

import asyncio
from datetime import datetime
from loguru import logger

try:
    from telegram import Bot
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Telegram notifications disabled.")


class TelegramNotifier:
    """
    Send trading notifications via Telegram

    Setup Instructions:
    1. Create a bot via @BotFather on Telegram
    2. Get the bot token from BotFather
    3. Start a chat with your bot
    4. Get your chat_id by messaging @userinfobot or visiting:
       https://api.telegram.org/bot<TOKEN>/getUpdates
    """

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = None
        self.enabled = False

        if TELEGRAM_AVAILABLE and bot_token and chat_id:
            self.bot = Bot(token=bot_token)
            self.enabled = True

    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send a message to Telegram"""
        if not self.enabled:
            logger.debug(f"Telegram disabled. Message: {message}")
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def send_sync(self, message: str):
        """Synchronous wrapper for send_message"""
        if not self.enabled:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.send_message(message))
            else:
                loop.run_until_complete(self.send_message(message))
        except:
            asyncio.run(self.send_message(message))

    def notify_trade_entry(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        stop_loss: float,
        strategy: str
    ):
        """Notify about trade entry"""
        emoji = "🟢" if action == "BUY" else "🔴"

        message = f"""
{emoji} <b>Trade Entry</b>

<b>Symbol:</b> {symbol}
<b>Action:</b> {action}
<b>Quantity:</b> {quantity}
<b>Price:</b> ₹{price:.2f}
<b>Stop Loss:</b> ₹{stop_loss:.2f}
<b>Strategy:</b> {strategy}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        self.send_sync(message.strip())

    def notify_trade_exit(
        self,
        symbol: str,
        action: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl: float,
        reason: str
    ):
        """Notify about trade exit"""
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "📈" if pnl > 0 else "📉"

        message = f"""
{emoji} <b>Trade Exit</b>

<b>Symbol:</b> {symbol}
<b>Action:</b> {action}
<b>Quantity:</b> {quantity}
<b>Entry:</b> ₹{entry_price:.2f}
<b>Exit:</b> ₹{exit_price:.2f}
{pnl_emoji} <b>P&L:</b> ₹{pnl:.2f}
<b>Reason:</b> {reason}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        self.send_sync(message.strip())

    def notify_stop_loss_update(
        self,
        symbol: str,
        old_sl: float,
        new_sl: float,
        reason: str
    ):
        """Notify about stop loss update"""
        direction = "⬆️" if new_sl > old_sl else "⬇️"

        message = f"""
{direction} <b>Stop Loss Updated</b>

<b>Symbol:</b> {symbol}
<b>Old SL:</b> ₹{old_sl:.2f}
<b>New SL:</b> ₹{new_sl:.2f}
<b>Reason:</b> {reason}
"""
        self.send_sync(message.strip())

    def notify_daily_summary(
        self,
        total_trades: int,
        winning_trades: int,
        daily_pnl: float,
        capital: float
    ):
        """Send daily trading summary"""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_pct = (daily_pnl / capital * 100) if capital > 0 else 0

        emoji = "🎉" if daily_pnl > 0 else "📊"

        message = f"""
{emoji} <b>Daily Summary</b>

<b>Total Trades:</b> {total_trades}
<b>Winning:</b> {winning_trades}
<b>Win Rate:</b> {win_rate:.1f}%
<b>Daily P&L:</b> ₹{daily_pnl:.2f} ({pnl_pct:+.2f}%)
<b>Capital:</b> ₹{capital:.2f}

<i>{datetime.now().strftime('%d %b %Y')}</i>
"""
        self.send_sync(message.strip())

    def notify_alert(self, title: str, message: str, level: str = "INFO"):
        """Send general alert"""
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "🚨",
            "SUCCESS": "✅"
        }
        emoji = emoji_map.get(level, "ℹ️")

        alert = f"""
{emoji} <b>{title}</b>

{message}
"""
        self.send_sync(alert.strip())

    def notify_system_start(self):
        """Notify system startup"""
        message = f"""
🚀 <b>Trading System Started</b>

<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
<b>Date:</b> {datetime.now().strftime('%d %b %Y')}

System is now monitoring markets...
"""
        self.send_sync(message.strip())

    def notify_system_stop(self, reason: str = "End of day"):
        """Notify system shutdown"""
        message = f"""
🛑 <b>Trading System Stopped</b>

<b>Reason:</b> {reason}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        self.send_sync(message.strip())
