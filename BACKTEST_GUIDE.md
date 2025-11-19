# Backtesting System Guide

## Overview

The backtesting system allows you to test trading strategies on historical data before risking real money.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Historical Data  →  Backtest Engine  →  Results       │
│                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │
│   │ Index Data  │    │  Simulate   │    │ Metrics   │  │
│   │ Option Data │ →  │  Trades     │ →  │ Reports   │  │
│   │ (Synthetic) │    │  P&L        │    │ Charts    │  │
│   └─────────────┘    └─────────────┘    └───────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Step 1: Download Historical Data

```bash
# Download 1 year of NIFTY data
python scripts/run_backtest.py download \
    --symbol NIFTY \
    --start-date 2023-01-01 \
    --end-date 2024-01-01
```

This will:
- Download daily OHLCV data from NSE/Yahoo Finance
- Generate synthetic option prices (since historical option data isn't free)
- Save to `data/historical/`

### Step 2: Run Backtest

```bash
# Test Bull Put Spread strategy
python scripts/run_backtest.py run \
    --symbol NIFTY \
    --strategy bull_put_spread \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --capital 10000
```

### Step 3: Review Results

```
============================================================
BACKTEST RESULTS
============================================================
Final Capital: ₹11,450
Total Return: ₹1,450 (+14.50%)
------------------------------------------------------------
Total Trades: 48
Win Rate: 62.5%
Profit Factor: 1.85
Sharpe Ratio: 1.42
Max Drawdown: 8.3%
------------------------------------------------------------
Average Win: ₹85
Average Loss: ₹52
============================================================

CRITERIA CHECK:
✅ Strategy PASSES minimum criteria
   Ready for paper trading!
```

---

## Commands Reference

### download - Get Historical Data

```bash
python scripts/run_backtest.py download \
    --symbol NIFTY \
    --start-date 2023-01-01 \
    --end-date 2024-01-01
```

**Parameters:**
- `--symbol`: NIFTY, BANKNIFTY, SENSEX
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)

**Output Files:**
- `data/historical/nifty_daily.csv` - Index OHLCV data
- `data/historical/nifty_options_synthetic.csv` - Generated option prices

### run - Execute Backtest

```bash
python scripts/run_backtest.py run \
    --symbol NIFTY \
    --strategy iron_condor \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --capital 50000
```

**Parameters:**
- `--symbol`: Symbol to backtest
- `--strategy`: Strategy name (iron_condor, bull_put_spread, bear_call_spread)
- `--start-date`: Backtest start
- `--end-date`: Backtest end
- `--capital`: Starting capital (default: from config)
- `--no-report`: Skip report generation

**Output Files:**
- `data/backtest_results/backtest_YYYY-MM-DD_YYYY-MM-DD.txt` - Text report
- `data/backtest_results/backtest_YYYY-MM-DD_YYYY-MM-DD.html` - Interactive charts
- `data/backtest_results/trades_YYYY-MM-DD_YYYY-MM-DD.csv` - Trade log

### compare - Compare Strategies

```bash
python scripts/run_backtest.py compare \
    --symbol NIFTY \
    --strategies "iron_condor,bull_put_spread,bear_call_spread" \
    --start-date 2023-01-01 \
    --end-date 2024-01-01
```

**Output:**
```
================================================================================
COMPARISON RESULTS
================================================================================
Strategy             Return %   Win Rate     Sharpe     Max DD   Trades
--------------------------------------------------------------------------------
iron_condor            +12.5%      58.0%       1.25       9.2%       42
bull_put_spread        +14.5%      62.5%       1.42       8.3%       48
bear_call_spread        +8.2%      55.0%       0.95      11.5%       45
================================================================================

Best strategy by Sharpe Ratio: bull_put_spread
```

---

## Performance Metrics Explained

### Return Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| Total Return | Absolute P&L | Positive |
| Return % | Percentage gain/loss | > 10% annual |
| CAGR | Compound Annual Growth Rate | > 15% |

### Risk Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Sharpe Ratio** | Risk-adjusted return | > 1.0 |
| **Sortino Ratio** | Downside risk-adjusted | > 1.5 |
| **Max Drawdown** | Largest peak-to-trough drop | < 15% |
| **Profit Factor** | Gross profit / Gross loss | > 1.5 |

### Trade Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Win Rate** | Winning trades % | > 50% |
| **Average Win** | Mean winning trade | > Avg Loss |
| **Expectancy** | Expected value per trade | Positive |

---

## Minimum Criteria for Live Trading

Before going live, your backtest should meet these criteria:

| Criteria | Minimum | Your Target |
|----------|---------|-------------|
| Win Rate | 50% | 55%+ |
| Profit Factor | 1.3 | 1.5+ |
| Sharpe Ratio | 0.8 | 1.2+ |
| Max Drawdown | < 15% | < 10% |
| Total Trades | 30+ | 100+ |

---

## Understanding the Reports

### Text Report

```
============================================================
BACKTEST REPORT
============================================================

Period: 2023-01-01 to 2024-01-01
Initial Capital: ₹10,000
Final Capital: ₹11,450

------------------------------------------------------------
TRADE LOG
------------------------------------------------------------
  # Date         Symbol               P&L       Reason
------------------------------------------------------------
  1 2023-01-05   NIFTY18000PE        +120      Target reached
  2 2023-01-12   NIFTY17900PE         -85      Stop loss hit
  3 2023-01-19   NIFTY18100PE        +145      Target reached
...
```

### HTML Report (Charts)

The HTML report includes:
1. **Equity Curve** - Capital over time
2. **Monthly Returns** - Bar chart of monthly P&L
3. **P&L Distribution** - Histogram of trade P&L
4. **Drawdown Chart** - Drawdown over time
5. **Strategy Breakdown** - Wins/losses by strategy
6. **Cumulative P&L** - Running total

---

## Configuration

### Backtest Settings

In `config/settings.yaml`:

```yaml
backtest:
  data_path: "data/historical"
  start_date: "2023-01-01"
  end_date: "2024-01-01"
  initial_capital: 10000
  commission: 20  # Per order in INR
```

### Strategy Settings

```yaml
strategies:
  bull_put_spread:
    enabled: true
    min_premium: 10      # Minimum ₹10 premium
    spread_width: 50     # ₹50 spread
    delta: 0.10          # Further OTM
```

---

## Important Notes

### Synthetic Option Data

Since historical option data is not freely available, the system generates **synthetic option prices** using a simplified pricing model.

**Limitations:**
- Approximates real premiums but not exact
- Doesn't capture IV spikes during events
- OI is estimated, not actual

**For production:**
- Purchase historical option data from NSE/BSE
- Or collect live snapshots daily over time

### Walk-Forward Testing

For more robust results, use walk-forward testing:

```bash
# Test on multiple periods
python scripts/run_backtest.py run --symbol NIFTY --strategy bull_put_spread --start-date 2022-01-01 --end-date 2022-06-30
python scripts/run_backtest.py run --symbol NIFTY --strategy bull_put_spread --start-date 2022-07-01 --end-date 2022-12-31
python scripts/run_backtest.py run --symbol NIFTY --strategy bull_put_spread --start-date 2023-01-01 --end-date 2023-06-30
```

If strategy performs consistently across all periods, it's more reliable.

### Overfitting Warning

If you optimize parameters to fit historical data perfectly, the strategy may fail in live trading. Signs of overfitting:
- Very high Sharpe ratio (> 3)
- Very low drawdown (< 3%)
- Too few trades (< 30)

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   1. DOWNLOAD DATA                                      │
│      python run_backtest.py download ...                │
│                      ↓                                  │
│   2. RUN BACKTEST                                       │
│      python run_backtest.py run ...                     │
│                      ↓                                  │
│   3. REVIEW METRICS                                     │
│      Check Win Rate, Sharpe, Drawdown                   │
│                      ↓                                  │
│   4. PASSES CRITERIA?                                   │
│      ├─ NO  → Adjust strategy parameters, go to 2       │
│      └─ YES → Continue to step 5                        │
│                      ↓                                  │
│   5. COMPARE STRATEGIES                                 │
│      python run_backtest.py compare ...                 │
│                      ↓                                  │
│   6. PAPER TRADE (2-4 weeks)                           │
│      Validate with live market data                     │
│                      ↓                                  │
│   7. LIVE TRADING                                       │
│      Start with minimum capital                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### "Data file not found"

```bash
# Download data first
python scripts/run_backtest.py download --symbol NIFTY --start-date 2023-01-01 --end-date 2024-01-01
```

### "No trades executed"

Possible causes:
- Premiums too low for minimum requirement
- Risk limits too tight
- Market conditions not suitable for strategy

Try:
- Lower `min_premium` in config
- Increase `max_capital_per_trade_pct`

### "Very few trades"

For statistical significance, you need at least 30 trades. Try:
- Extend backtest period
- Lower minimum premium threshold
- Enable more strategies

### "Sharpe ratio is 0 or negative"

Strategy is not profitable or too volatile. Try:
- Different strategy
- Adjust stop-loss settings
- Wider spread width

---

## Next Steps After Successful Backtest

1. **Paper trade for 2-4 weeks** - Run with live data but no real money
2. **Review paper trading results** - Verify backetest performance holds
3. **Start live with 25% capital** - Test with real money, small size
4. **Scale up gradually** - Increase position size as confidence builds

---

## Files Created

| File | Location | Description |
|------|----------|-------------|
| Data Loader | `src/backtest/data_loader.py` | Download historical data |
| Engine | `src/backtest/engine.py` | Core backtesting logic |
| Metrics | `src/backtest/metrics.py` | Performance calculations |
| Visualizer | `src/backtest/visualizer.py` | Charts and reports |
| Runner | `scripts/run_backtest.py` | CLI tool |

---

Ready to start backtesting! Run:

```bash
# Download data
python scripts/run_backtest.py download --symbol NIFTY --start-date 2023-01-01 --end-date 2024-01-01

# Run backtest with your capital
python scripts/run_backtest.py run --symbol NIFTY --strategy bull_put_spread --start-date 2023-01-01 --end-date 2024-01-01 --capital 10000
```
