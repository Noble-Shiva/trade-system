# Setup Guide - BSE F&O Trading System

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Broker

#### Option A: Zerodha Kite

1. **Get API Access**
   - Go to [Kite Connect](https://kite.trade/)
   - Create an app (₹2,000/month)
   - Get API Key and API Secret

2. **Setup Credentials**
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   BROKER_API_KEY=your_api_key
   BROKER_API_SECRET=your_api_secret
   ```

3. **Update Config**
   In `config/settings.yaml`:
   ```yaml
   broker:
     name: "zerodha"
   ```

#### Option B: Angel One (Free API)

1. **Get API Access**
   - Login to [Angel One SmartAPI](https://smartapi.angelbroking.com/)
   - Create an app (FREE)
   - Get API Key

2. **Generate TOTP Secret**
   - Enable TOTP in Angel One app
   - Get the TOTP secret for automation

3. **Setup Credentials**
   ```
   BROKER_API_KEY=your_api_key
   BROKER_API_SECRET=your_password
   BROKER_USER_ID=your_client_id
   ANGEL_TOTP_SECRET=your_totp_secret
   ```

4. **Update Config**
   ```yaml
   broker:
     name: "angel"
   ```

#### Option C: Groww (Free API)

1. **Get API Access**
   - Login to [Groww Trade API](https://groww.in/trade-api)
   - Go to [API Keys page](https://groww.in/trade-api/api-keys)
   - Create API Key and Secret

2. **Choose Authentication Method**

   **Method 1: TOTP (Recommended for automation)**
   - Scan QR code with authenticator app
   - Get TOTP secret from Groww

   ```
   BROKER_API_KEY=your_groww_api_key
   BROKER_API_SECRET=not_needed_for_totp
   GROWW_TOTP_SECRET=your_totp_secret
   ```

   **Method 2: API Key + Secret**
   - Requires daily approval on Groww Cloud API Keys page

   ```
   BROKER_API_KEY=your_groww_api_key
   BROKER_API_SECRET=your_groww_secret
   ```

3. **Update Config**
   ```yaml
   broker:
     name: "groww"
   ```

4. **Install Groww SDK**
   ```bash
   pip install growwapi pyotp
   ```

**Features:**
- ✅ Free API access
- ✅ Equity, F&O, Commodity support
- ✅ Option chain with Greeks
- ✅ Up to 15 orders/sec

**Rate Limits:**
- Orders: 15/sec, 250/min
- Live Data: 10/sec, 300/min
- Position/Status: 20/sec, 500/min

---

## Telegram Notifications Setup

### Step 1: Create Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the **Bot Token**

### Step 2: Get Chat ID

1. Start a chat with your new bot
2. Send any message to it
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` - that's your Chat ID

### Step 3: Configure

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Step 4: Test

```python
from src.notifications import TelegramNotifier

notifier = TelegramNotifier(
    bot_token="your_token",
    chat_id="your_chat_id"
)
notifier.notify_alert("Test", "Telegram setup working!", "SUCCESS")
```

---

## Configuration

### Capital Settings

In `config/settings.yaml`:

```yaml
capital:
  initial: 10000  # Your starting capital

risk:
  max_capital_per_trade_pct: 5.0   # Max 5% per trade
  max_daily_loss_pct: 2.0          # Stop after 2% daily loss
  max_open_positions: 2            # Max 2 positions for small capital
```

### Strategy Settings

For ₹5,000-10,000 capital, use conservative settings:

```yaml
strategies:
  active:
    - "bull_put_spread"  # Lower margin requirement

  bull_put_spread:
    enabled: true
    min_premium: 20      # Lower premium threshold
    spread_width: 50     # Smaller spread = less margin
```

### Trading Hours

```yaml
market:
  trading_hours:
    start: "09:15"
    end: "15:30"
    no_new_trades_after: "14:30"  # No new trades after 2:30 PM
```

---

## Running the System

### Paper Trading (Recommended First)

```bash
python scripts/start_trading.py --paper
```

### Live Trading

```bash
python scripts/start_trading.py
```

### With Debug Logs

```bash
python scripts/start_trading.py --log-level DEBUG
```

---

## Sample Telegram Messages

### Trade Entry
```
🔴 Trade Entry

Symbol: NIFTY24500PE
Action: SELL
Quantity: 1
Price: ₹150.00
Stop Loss: ₹300.00
Strategy: bull_put_spread
Time: 09:45:23
```

### Stop Loss Update
```
⬆️ Stop Loss Updated

Symbol: NIFTY24500PE
Old SL: ₹300.00
New SL: ₹225.00
Reason: Trailing SL (profit 2.5%)
```

### Daily Summary
```
🎉 Daily Summary

Total Trades: 4
Winning: 3
Win Rate: 75.0%
Daily P&L: ₹850.00 (+8.50%)
Capital: ₹10,850.00

19 Nov 2024
```

---

## Troubleshooting

### "Module not found" Error
```bash
pip install -r requirements.txt
```

### Broker Login Failed
- Verify credentials in `.env`
- For Zerodha: Check if access token is valid
- For Angel: Verify TOTP is correct

### No Trades Executing
- Check if market is open (9:15 AM - 3:30 PM IST)
- Verify capital meets minimum (₹10,000+ recommended)
- Check VIX level (system pauses if VIX > 25)

### Telegram Not Working
- Verify bot token and chat ID
- Make sure you've started a chat with your bot
- Check if `python-telegram-bot` is installed

---

## Important Notes

### Capital Requirements

| Strategy | Min Capital | Recommended |
|----------|-------------|-------------|
| Bull Put Spread | ₹10,000 | ₹25,000 |
| Iron Condor | ₹15,000 | ₹50,000 |

⚠️ **With ₹5,000-10,000**: You can only trade 1 lot of weekly options with tight spreads.

### Risk Warning

- Start with paper trading
- Never risk more than you can afford to lose
- This system is for educational purposes
- Past performance doesn't guarantee future results

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure broker credentials
3. ✅ Set up Telegram notifications
4. ✅ Run in paper trading mode
5. ⏳ Analyze results for 2-4 weeks
6. ⏳ Go live with minimum capital
7. ⏳ Scale gradually as confidence builds
