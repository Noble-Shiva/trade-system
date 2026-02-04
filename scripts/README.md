# Backtesting Scripts - Quick Reference

## 🚀 Quick Start (One Command)

```bash
# Run complete backtest with defaults
python scripts/quick_backtest.py
```

That's it! This will:
- Download 1 year of NIFTY data
- Generate option prices
- Test all 3 strategies
- Show which is best
- Generate reports

---

## Scripts Available

### 1. `quick_backtest.py` - Complete Workflow ⭐ RECOMMENDED

**Run everything in one go:**

```bash
# Default: NIFTY, 1 year, ₹10,000
python scripts/quick_backtest.py

# Custom symbol and capital
python scripts/quick_backtest.py --symbol BANKNIFTY --capital 25000

# Quick test (3 months only)
python scripts/quick_backtest.py --quick

# Different time period
python scripts/quick_backtest.py --months 6

# Use existing data
python scripts/quick_backtest.py --skip-download
```

**Output:**
```
[1/5] Downloading Historical Data
✅ Downloaded 252 days of index data

[2/5] Generating Synthetic Option Data
✅ Generated 7,560 option records

[3/5] Running Backtests for All Strategies
  [1/3] Testing: Iron Condor
    Return: +12.5% | Win Rate: 58% | Trades: 42 | Sharpe: 1.25
  [2/3] Testing: Bull Put Spread
    Return: +14.5% | Win Rate: 62% | Trades: 48 | Sharpe: 1.42
  [3/3] Testing: Bear Call Spread
    Return: +8.2% | Win Rate: 55% | Trades: 45 | Sharpe: 0.95

[4/5] Strategy Comparison
🏆 Best Strategy: Bull Put Spread

✅ READY FOR PAPER TRADING!

[5/5] Generating Reports
📊 All reports saved to: data/backtest_results/
```

---

### 2. `run_backtest.py` - Advanced Control

**For more control over individual steps:**

```bash
# Download data
python scripts/run_backtest.py download \
    --symbol NIFTY \
    --start-date 2023-01-01 \
    --end-date 2024-01-01

# Run single strategy
python scripts/run_backtest.py run \
    --symbol NIFTY \
    --strategy bull_put_spread \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --capital 10000

# Compare strategies
python scripts/run_backtest.py compare \
    --symbol NIFTY \
    --strategies "iron_condor,bull_put_spread,bear_call_spread" \
    --start-date 2023-01-01 \
    --end-date 2024-01-01
```

---

## Command-Line Options

### quick_backtest.py

| Option | Default | Description |
|--------|---------|-------------|
| `--symbol` | NIFTY | Index to test (NIFTY, BANKNIFTY, SENSEX) |
| `--capital` | 10000 | Starting capital in ₹ |
| `--months` | 12 | How many months back to test |
| `--quick` | - | Fast test with 3 months only |
| `--skip-download` | - | Use existing data |

---

## Examples

### For ₹10,000 Capital

```bash
# Test with your capital
python scripts/quick_backtest.py --capital 10000
```

### For ₹25,000 Capital

```bash
# More capital = can test all strategies
python scripts/quick_backtest.py --capital 25000 --symbol BANKNIFTY
```

### Quick Test (Fast)

```bash
# Just want to see if it works?
python scripts/quick_backtest.py --quick
```

### Test Different Periods

```bash
# Last 6 months
python scripts/quick_backtest.py --months 6

# Last 18 months
python scripts/quick_backtest.py --months 18
```

### Multiple Runs

```bash
# Test NIFTY
python scripts/quick_backtest.py --symbol NIFTY

# Test BANKNIFTY
python scripts/quick_backtest.py --symbol BANKNIFTY

# Test SENSEX
python scripts/quick_backtest.py --symbol SENSEX
```

---

## Understanding Output

### Success Criteria

Your strategy is ready for paper trading when:

| Metric | Target | What It Means |
|--------|--------|---------------|
| **Win Rate** | > 50% | More winning trades than losing |
| **Profit Factor** | > 1.3 | Wins are bigger than losses |
| **Sharpe Ratio** | > 0.8 | Good risk-adjusted returns |
| **Max Drawdown** | < 15% | Limited worst-case loss |

### Status Indicators

- ✅ **PASS** - Strategy meets all criteria, ready for paper trading
- ❌ **FAIL** - Strategy needs improvement, adjust parameters

---

## Output Files

After running, check:

```
data/backtest_results/
├── bull_put_spread_NIFTY_2023-01-01_2024-01-01.txt     # Text report
├── bull_put_spread_NIFTY_2023-01-01_2024-01-01.html    # Interactive charts
├── bull_put_spread_NIFTY_2023-01-01_2024-01-01_trades.csv  # Trade log
├── iron_condor_NIFTY_2023-01-01_2024-01-01.txt
├── iron_condor_NIFTY_2023-01-01_2024-01-01.html
└── ...
```

---

## Troubleshooting

### "Config file not found"

```bash
# Make sure you're in the project root
cd /home/user/trade-system

# Check config exists
ls config/settings.yaml
```

### "Data download failed"

```bash
# Check internet connection
# Or use existing data
python scripts/quick_backtest.py --skip-download
```

### "No trades executed"

Possible causes:
- Capital too low (increase --capital)
- Premium requirements too high (edit config/settings.yaml)

Solution:
```yaml
# config/settings.yaml
strategies:
  bull_put_spread:
    min_premium: 5  # Lower this
```

### "Import errors"

```bash
# Install dependencies
pip install -r requirements.txt
```

---

## Workflow Recommendation

```
1. Quick Test (5 minutes)
   python scripts/quick_backtest.py --quick

2. Full Test (15 minutes)
   python scripts/quick_backtest.py

3. Review Reports
   Open data/backtest_results/*.html

4. Adjust if Needed
   Edit config/settings.yaml

5. Test Again
   python scripts/quick_backtest.py

6. Paper Trade
   When strategy shows ✅ PASS
```

---

## What Gets Tested?

### Strategies

1. **Iron Condor** - Neutral strategy, range-bound markets
2. **Bull Put Spread** - Slightly bullish, credit spread
3. **Bear Call Spread** - Slightly bearish, credit spread

### For Each Strategy

- Entry signals
- Exit conditions
- Stop-loss management
- Position sizing
- Risk limits
- P&L tracking

---

## Important Notes

⚠️ **Synthetic Data**: Option prices are generated using a pricing model, not actual historical prices.

✅ **Good For**: Testing strategy logic, risk management, position sizing

❌ **Not Exact**: Actual premiums may vary in live trading

🎯 **Solution**: Use results as guideline, verify with paper trading before going live

---

## Next Steps After Backtest

1. **If ✅ PASS**:
   - Run paper trading for 2-4 weeks
   - Verify live data matches expectations
   - Start with minimum capital

2. **If ❌ FAIL**:
   - Review failure reasons
   - Adjust strategy parameters
   - Test different time periods
   - Try different strategies

---

## Getting Help

1. Check `BACKTEST_GUIDE.md` for detailed explanation
2. Review `IMPLEMENTATION_STATUS.md` for system status
3. See sample reports in `data/backtest_results/`

---

## Quick Reference Card

```bash
# Most Common Commands

# Default backtest
python scripts/quick_backtest.py

# Your capital
python scripts/quick_backtest.py --capital 10000

# Quick test
python scripts/quick_backtest.py --quick

# Different symbol
python scripts/quick_backtest.py --symbol BANKNIFTY

# Longer period
python scripts/quick_backtest.py --months 18

# Help
python scripts/quick_backtest.py --help
```

---

**Ready to backtest? Run:** `python scripts/quick_backtest.py`
