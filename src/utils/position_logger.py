"""
Position Logger - Periodic logging of open positions
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Callable
from loguru import logger


class PositionLogger:
    """
    Periodically logs position status to console and/or callback
    
    Usage:
        logger = PositionLogger(interval_seconds=60)
        logger.start(get_positions_func)
        # ... trading ...
        logger.stop()
    """
    
    def __init__(
        self,
        interval_seconds: int = 60,
        callback: Callable[[List[dict]], None] = None
    ):
        self.interval = interval_seconds
        self.callback = callback
        self._running = False
        self._thread = None
        self._positions_func = None
    
    def start(self, get_positions: Callable[[], List[dict]]):
        """Start periodic logging"""
        if self._running:
            logger.warning("Position logger already running")
            return
        
        self._positions_func = get_positions
        self._running = True
        self._thread = threading.Thread(target=self._log_loop, daemon=True)
        self._thread.start()
        logger.info(f"📊 Position logger started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop periodic logging"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("📊 Position logger stopped")
    
    def _log_loop(self):
        """Main logging loop"""
        while self._running:
            try:
                positions = self._positions_func()
                self._log_positions(positions)
                
                if self.callback:
                    self.callback(positions)
                    
            except Exception as e:
                logger.error(f"Position logger error: {e}")
            
            # Sleep in small intervals to check _running flag
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def _log_positions(self, positions: List[dict]):
        """Log positions to console"""
        if not positions:
            logger.info("📊 No open positions")
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print("\n" + "=" * 70)
        print(f"📊 POSITION STATUS [{timestamp}]")
        print("=" * 70)
        print(f"{'Symbol':<20} {'Side':<8} {'Qty':<6} {'Avg':<12} {'LTP':<12} {'P&L':<12}")
        print("-" * 70)
        
        total_pnl = 0
        for pos in positions:
            symbol = pos.get("symbol", "")[:20]
            side = pos.get("side", "")
            qty = pos.get("quantity", 0)
            avg = pos.get("avg_price", 0)
            ltp = pos.get("current_price", pos.get("ltp", avg))
            
            # Calculate P&L
            if side == "LONG" or side == "BUY":
                pnl = (ltp - avg) * qty
            else:
                pnl = (avg - ltp) * qty
            
            total_pnl += pnl
            pnl_str = f"₹{pnl:+,.2f}"
            
            print(f"{symbol:<20} {side:<8} {qty:<6} ₹{avg:<10,.2f} ₹{ltp:<10,.2f} {pnl_str:<12}")
        
        print("-" * 70)
        print(f"{'TOTAL P&L':<58} ₹{total_pnl:+,.2f}")
        print("=" * 70 + "\n")


def format_position_message(positions: List[dict]) -> str:
    """Format positions for Telegram/notification"""
    if not positions:
        return "📊 No open positions"
    
    lines = ["📊 *Position Update*", ""]
    
    total_pnl = 0
    for pos in positions:
        symbol = pos.get("symbol", "")
        side = pos.get("side", "")
        qty = pos.get("quantity", 0)
        avg = pos.get("avg_price", 0)
        ltp = pos.get("current_price", pos.get("ltp", avg))
        
        if side in ["LONG", "BUY"]:
            pnl = (ltp - avg) * qty
        else:
            pnl = (avg - ltp) * qty
        
        total_pnl += pnl
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        lines.append(f"{emoji} *{symbol}*")
        lines.append(f"   {side} {qty} @ ₹{avg:.2f}")
        lines.append(f"   LTP: ₹{ltp:.2f} | P&L: ₹{pnl:+,.2f}")
        lines.append("")
    
    lines.append(f"*Total P&L: ₹{total_pnl:+,.2f}*")
    
    return "\n".join(lines)
