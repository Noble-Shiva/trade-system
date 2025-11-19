"""
Market Calendar for NSE India
Handles trading holidays, expiry dates, and market hours
"""

from datetime import datetime, timedelta, time
from typing import List, Optional
import pytz
from src.utils.logger import TradingLogger

logger = TradingLogger("MarketCalendar")


class NSECalendar:
    """NSE Market Calendar - Trading days, holidays, and expiry dates"""

    # Indian timezone
    IST = pytz.timezone('Asia/Kolkata')

    # NSE trading hours
    MARKET_OPEN = time(9, 15)  # 9:15 AM
    MARKET_CLOSE = time(15, 30)  # 3:30 PM
    PRE_OPEN_START = time(9, 0)  # 9:00 AM
    PRE_OPEN_END = time(9, 15)  # 9:15 AM

    # NSE holidays for 2025 (update annually)
    # Source: https://www.nseindia.com/regulations/trading-holidays
    HOLIDAYS_2025 = [
        datetime(2025, 1, 26),  # Republic Day
        datetime(2025, 3, 14),  # Holi
        datetime(2025, 3, 31),  # Id-Ul-Fitr (Ramadan Eid)
        datetime(2025, 4, 10),  # Mahavir Jayanti
        datetime(2025, 4, 14),  # Dr. Ambedkar Jayanti
        datetime(2025, 4, 18),  # Good Friday
        datetime(2025, 5, 1),   # Maharashtra Day
        datetime(2025, 6, 7),   # Id-Ul-Adha (Bakri Id)
        datetime(2025, 7, 6),   # Muharram
        datetime(2025, 8, 15),  # Independence Day
        datetime(2025, 8, 27),  # Ganesh Chaturthi
        datetime(2025, 10, 2),  # Mahatma Gandhi Jayanti
        datetime(2025, 10, 21), # Dussehra
        datetime(2025, 10, 22), # Dussehra (additional)
        datetime(2025, 11, 5),  # Diwali Laxmi Pujan
        datetime(2025, 11, 6),  # Diwali Balipratipada
        datetime(2025, 11, 24), # Gurunanak Jayanti
        datetime(2025, 12, 25), # Christmas
    ]

    # NSE holidays for 2024 (for historical reference)
    HOLIDAYS_2024 = [
        datetime(2024, 1, 26),  # Republic Day
        datetime(2024, 3, 8),   # Maha Shivratri
        datetime(2024, 3, 25),  # Holi
        datetime(2024, 3, 29),  # Good Friday
        datetime(2024, 4, 11),  # Id-Ul-Fitr
        datetime(2024, 4, 17),  # Ram Navami
        datetime(2024, 4, 21),  # Mahavir Jayanti
        datetime(2024, 5, 1),   # Maharashtra Day
        datetime(2024, 6, 17),  # Id-Ul-Adha
        datetime(2024, 7, 17),  # Muharram
        datetime(2024, 8, 15),  # Independence Day
        datetime(2024, 10, 2),  # Mahatma Gandhi Jayanti
        datetime(2024, 10, 12), # Dussehra
        datetime(2024, 11, 1),  # Diwali Laxmi Pujan
        datetime(2024, 11, 15), # Gurunanak Jayanti
        datetime(2024, 12, 25), # Christmas
    ]

    def __init__(self):
        """Initialize NSE Calendar"""
        self.holidays = self._get_all_holidays()
        logger.info(f"NSE Calendar initialized with {len(self.holidays)} holidays")

    def _get_all_holidays(self) -> List[datetime]:
        """Get all holidays (2024 + 2025)"""
        return sorted(self.HOLIDAYS_2024 + self.HOLIDAYS_2025)

    @staticmethod
    def now() -> datetime:
        """Get current time in IST"""
        return datetime.now(NSECalendar.IST)

    def is_holiday(self, date: datetime) -> bool:
        """
        Check if given date is a holiday

        Args:
            date: Date to check

        Returns:
            True if holiday, False otherwise
        """
        # Normalize to date only (remove time)
        check_date = datetime(date.year, date.month, date.day)

        return check_date in self.holidays

    def is_weekend(self, date: datetime) -> bool:
        """
        Check if given date is a weekend

        Args:
            date: Date to check

        Returns:
            True if Saturday or Sunday, False otherwise
        """
        return date.weekday() in [5, 6]  # 5=Saturday, 6=Sunday

    def is_trading_day(self, date: datetime) -> bool:
        """
        Check if given date is a trading day

        Args:
            date: Date to check

        Returns:
            True if trading day, False otherwise
        """
        return not (self.is_weekend(date) or self.is_holiday(date))

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open

        Args:
            dt: Datetime to check (default: now)

        Returns:
            True if market is open, False otherwise
        """
        if dt is None:
            dt = self.now()

        # Check if trading day
        if not self.is_trading_day(dt):
            return False

        # Check if within trading hours
        current_time = dt.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE

    def next_trading_day(self, date: datetime) -> datetime:
        """
        Get next trading day from given date

        Args:
            date: Starting date

        Returns:
            Next trading day
        """
        next_day = date + timedelta(days=1)

        # Keep incrementing until we find a trading day
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)

        return next_day

    def previous_trading_day(self, date: datetime) -> datetime:
        """
        Get previous trading day from given date

        Args:
            date: Starting date

        Returns:
            Previous trading day
        """
        prev_day = date - timedelta(days=1)

        # Keep decrementing until we find a trading day
        while not self.is_trading_day(prev_day):
            prev_day -= timedelta(days=1)

        return prev_day

    def get_last_thursday(self, year: int, month: int) -> datetime:
        """
        Get last Thursday of a given month (NIFTY expiry)

        Args:
            year: Year
            month: Month

        Returns:
            Last Thursday of the month
        """
        # Get last day of month
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)

        # Thursday is weekday 3
        # Go backward from last day until we find a Thursday
        while last_day.weekday() != 3:
            last_day -= timedelta(days=1)

        return last_day

    def get_last_wednesday(self, year: int, month: int) -> datetime:
        """
        Get last Wednesday of a given month (BANKNIFTY expiry)

        Args:
            year: Year
            month: Month

        Returns:
            Last Wednesday of the month
        """
        # Get last day of month
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)

        # Wednesday is weekday 2
        # Go backward from last day until we find a Wednesday
        while last_day.weekday() != 2:
            last_day -= timedelta(days=1)

        return last_day

    def get_monthly_expiry_nifty(self, year: int, month: int) -> datetime:
        """
        Get monthly expiry for NIFTY (last Thursday, unless holiday)

        Args:
            year: Year
            month: Month

        Returns:
            NIFTY monthly expiry date
        """
        expiry = self.get_last_thursday(year, month)

        # If expiry falls on holiday, move to previous trading day
        while not self.is_trading_day(expiry):
            expiry = self.previous_trading_day(expiry)

        return expiry

    def get_monthly_expiry_banknifty(self, year: int, month: int) -> datetime:
        """
        Get monthly expiry for BANKNIFTY (last Wednesday, unless holiday)

        Args:
            year: Year
            month: Month

        Returns:
            BANKNIFTY monthly expiry date
        """
        expiry = self.get_last_wednesday(year, month)

        # If expiry falls on holiday, move to previous trading day
        while not self.is_trading_day(expiry):
            expiry = self.previous_trading_day(expiry)

        return expiry

    def get_weekly_expiry_nifty(self, date: datetime) -> datetime:
        """
        Get weekly expiry for NIFTY (upcoming Thursday)

        Args:
            date: Reference date

        Returns:
            Upcoming Thursday (NIFTY weekly expiry)
        """
        # Thursday is weekday 3
        days_ahead = 3 - date.weekday()

        # If today is Thursday or past Thursday, get next Thursday
        if days_ahead <= 0:
            days_ahead += 7

        expiry = date + timedelta(days=days_ahead)

        # If expiry falls on holiday, move to previous trading day
        while not self.is_trading_day(expiry):
            expiry = self.previous_trading_day(expiry)

        return expiry

    def get_weekly_expiry_banknifty(self, date: datetime) -> datetime:
        """
        Get weekly expiry for BANKNIFTY (upcoming Wednesday)

        Args:
            date: Reference date

        Returns:
            Upcoming Wednesday (BANKNIFTY weekly expiry)
        """
        # Wednesday is weekday 2
        days_ahead = 2 - date.weekday()

        # If today is Wednesday or past Wednesday, get next Wednesday
        if days_ahead <= 0:
            days_ahead += 7

        expiry = date + timedelta(days=days_ahead)

        # If expiry falls on holiday, move to previous trading day
        while not self.is_trading_day(expiry):
            expiry = self.previous_trading_day(expiry)

        return expiry

    def days_to_expiry(self, expiry_date: datetime, from_date: Optional[datetime] = None) -> int:
        """
        Calculate days remaining to expiry

        Args:
            expiry_date: Expiry date
            from_date: From date (default: today)

        Returns:
            Number of days to expiry
        """
        if from_date is None:
            from_date = self.now()

        # Count only trading days
        count = 0
        current = from_date

        while current.date() < expiry_date.date():
            current = self.next_trading_day(current)
            count += 1

        return count

    def trading_days_in_range(self, start_date: datetime, end_date: datetime) -> int:
        """
        Count trading days in a date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Number of trading days
        """
        count = 0
        current = start_date

        while current.date() <= end_date.date():
            if self.is_trading_day(current):
                count += 1
            current += timedelta(days=1)

        return count


# Create global calendar instance
calendar = NSECalendar()


if __name__ == "__main__":
    print("NSE Market Calendar Test")
    print("=" * 60)

    cal = NSECalendar()
    now = cal.now()

    print(f"\nCurrent Time (IST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Is Trading Day: {cal.is_trading_day(now)}")
    print(f"Is Market Open: {cal.is_market_open(now)}")

    print(f"\nNext Trading Day: {cal.next_trading_day(now).strftime('%Y-%m-%d')}")
    print(f"Previous Trading Day: {cal.previous_trading_day(now).strftime('%Y-%m-%d')}")

    print(f"\n{'NIFTY Expiries (Nov-Dec 2025)':^60}")
    print("-" * 60)

    # Monthly expiries
    print(f"Nov 2025 Monthly (NIFTY):     {cal.get_monthly_expiry_nifty(2025, 11).strftime('%Y-%m-%d %A')}")
    print(f"Dec 2025 Monthly (NIFTY):     {cal.get_monthly_expiry_nifty(2025, 12).strftime('%Y-%m-%d %A')}")

    print(f"\n{'BANKNIFTY Expiries (Nov-Dec 2025)':^60}")
    print("-" * 60)
    print(f"Nov 2025 Monthly (BANKNIFTY): {cal.get_monthly_expiry_banknifty(2025, 11).strftime('%Y-%m-%d %A')}")
    print(f"Dec 2025 Monthly (BANKNIFTY): {cal.get_monthly_expiry_banknifty(2025, 12).strftime('%Y-%m-%d %A')}")

    print(f"\n{'Weekly Expiries (This Week)':^60}")
    print("-" * 60)
    print(f"NIFTY Weekly Expiry:     {cal.get_weekly_expiry_nifty(now).strftime('%Y-%m-%d %A')}")
    print(f"BANKNIFTY Weekly Expiry: {cal.get_weekly_expiry_banknifty(now).strftime('%Y-%m-%d %A')}")

    nifty_expiry = cal.get_weekly_expiry_nifty(now)
    days_left = cal.days_to_expiry(nifty_expiry)
    print(f"\nDays to NIFTY Expiry: {days_left}")

    print(f"\n{'NSE Holidays 2025':^60}")
    print("-" * 60)
    for holiday in cal.HOLIDAYS_2025:
        print(f"{holiday.strftime('%Y-%m-%d %A')} - NSE Holiday")

    print("\n" + "=" * 60)
    print("✅ Market Calendar Working Successfully!")
