# Implementation Phases - Micro-Capital (₹5-10K) Trading System

**Optimized for faster deployment with small capital**

---

## Phase Overview

| Phase | Timeline | Focus | Status |
|-------|----------|-------|--------|
| Phase 0 | Week 1 | Setup & Infrastructure | ✅ COMPLETE |
| Phase 1 | Week 2 | Data Pipeline | ⏳ IN PROGRESS |
| Phase 2 | Week 3 | First Strategy + Backtesting | ⏳ NEXT |
| Phase 3 | Week 4 | Risk Management + Execution | ⏳ PENDING |
| Phase 4 | Week 5 | Paper Trading | ⏳ PENDING |
| Phase 5 | Week 6+ | Live Trading (₹5K) | ⏳ PENDING |
| Phase 6 | Ongoing | Optimization & Scaling | ⏳ PENDING |

---

## ✅ Phase 0: Setup & Infrastructure (Week 1) - COMPLETE!

### Goals
- Set up Python development environment
- Install all dependencies
- Create project structure
- Build utility modules

### Deliverables
- ✅ Python 3.11.14 installed
- ✅ Virtual environment created
- ✅ Angel One SDK installed (smartapi-python)
- ✅ 17 core packages installed (pandas, numpy, scipy, matplotlib, etc.)
- ✅ Project directory structure created
- ✅ Configuration files ready (.env, config.yaml)
- ✅ Utility modules created and tested:
  - config_loader.py ✅
  - logger.py ✅
  - angel_one_helper.py ✅
- ✅ Documentation complete

### Time Spent: Week 1
### Status: ✅ COMPLETE

**What's Working:**
- Configuration loading from YAML
- Logging to file and console
- Angel One SDK ready (needs credentials)
- All imports successful

**Blockers:**
- ⏳ Waiting for Angel One API credentials (2-3 days)
- Can proceed with Phase 1 in parallel

---

## ⏳ Phase 1: Data Pipeline (Week 2) - CURRENT PHASE

### Goals
- Download historical data for backtesting
- Set up real-time data stream (when API ready)
- Create market calendar utilities
- Data quality checks

### Tasks

#### 1.1 Market Calendar (Start Now - No API Needed)
- [ ] Create `src/data/market_calendar.py`
- [ ] Implement NSE holiday calendar
- [ ] Calculate expiry dates (last Thursday for NIFTY, Wednesday for BANKNIFTY)
- [ ] Check if market is open function
- [ ] Get next/previous trading day
- [ ] **Estimated Time:** 2-3 hours

#### 1.2 Historical Data Downloader (Needs Angel One API)
- [ ] Create `src/data/historical_downloader.py`
- [ ] Download NIFTY spot data (5 years)
- [ ] Download BANKNIFTY spot data (5 years)
- [ ] Download NIFTY options data (1 year - for backtesting)
- [ ] Download BANKNIFTY options data (1 year)
- [ ] Store in CSV format in `data/historical/`
- [ ] Data validation and quality checks
- [ ] **Estimated Time:** 4-6 hours (once API ready)

#### 1.3 Real-time Data Stream (Needs Angel One API)
- [ ] Create `src/data/live_data.py`
- [ ] WebSocket connection to Angel One
- [ ] Subscribe to NIFTY/BANKNIFTY live feeds
- [ ] Parse and normalize tick data
- [ ] Store in memory/cache for strategy use
- [ ] Error handling and reconnection logic
- [ ] **Estimated Time:** 4-6 hours

#### 1.4 Data Quality Module
- [ ] Create `src/data/quality_check.py`
- [ ] Detect missing data points
- [ ] Detect outliers (price spikes)
- [ ] Fill missing data (interpolation)
- [ ] Data validation rules
- [ ] **Estimated Time:** 2-3 hours

### Deliverables
- [ ] Market calendar working (holidays, expiries)
- [ ] 5 years of historical index data downloaded
- [ ] 1 year of options data downloaded
- [ ] Real-time data streaming working
- [ ] Data quality checks in place
- [ ] Sample data available for strategy testing

### Dependencies
- ⏳ Angel One API credentials (for 1.2 and 1.3)
- ✅ config_loader.py (already done)
- ✅ logger.py (already done)

### Timeline: Week 2 (can start 1.1 now, 1.2-1.3 when API ready)

### Success Criteria
- ✓ Can fetch NIFTY price for any date in last 5 years
- ✓ Can get current NIFTY/BANKNIFTY price in real-time
- ✓ Know market hours and holidays
- ✓ Data quality > 99%

---

## ⏳ Phase 2: First Strategy + Backtesting (Week 3)

### Goals
- Implement ONE simple strategy (momentum-based)
- Backtest on historical data
- Verify profitability
- Optimize parameters

### Tasks

#### 2.1 Technical Indicators
- [ ] Create `src/utils/indicators.py`
- [ ] Implement moving averages (SMA, EMA)
- [ ] Implement RSI
- [ ] Implement ATR (for stop loss)
- [ ] Implement MACD
- [ ] Test all indicators with sample data
- [ ] **Estimated Time:** 3-4 hours

#### 2.2 Momentum Strategy (Options Buying)
- [ ] Create `src/strategies/momentum_options.py`
- [ ] Entry logic: Strong momentum + RSI confirmation
- [ ] Select ATM/OTM call or put based on direction
- [ ] Calculate position size (for ₹10K capital)
- [ ] Set stop loss (35-40% of premium)
- [ ] Set target (2:1 reward-risk)
- [ ] Exit logic: Target/SL/EOD
- [ ] **Estimated Time:** 4-5 hours

#### 2.3 Backtesting Setup
- [ ] Install backtesting.py library
- [ ] Create `src/backtesting/backtest_runner.py`
- [ ] Adapt backtesting.py for options trading
- [ ] Configure for Indian markets
- [ ] Run first backtest on NIFTY (1 year)
- [ ] **Estimated Time:** 3-4 hours

#### 2.4 Performance Analysis
- [ ] Create `src/backtesting/performance_metrics.py`
- [ ] Calculate Sharpe ratio
- [ ] Calculate max drawdown
- [ ] Calculate win rate
- [ ] Calculate profit factor
- [ ] Generate equity curve
- [ ] **Estimated Time:** 2-3 hours

#### 2.5 Strategy Optimization
- [ ] Parameter grid search (RSI threshold, holding period, etc.)
- [ ] Walk-forward analysis
- [ ] Select best parameters
- [ ] Verify on out-of-sample data
- [ ] **Estimated Time:** 3-4 hours

### Deliverables
- [ ] Momentum strategy fully implemented
- [ ] Backtested on 1 year of data
- [ ] Sharpe ratio > 1.5
- [ ] Win rate > 50%
- [ ] Max drawdown < 20%
- [ ] Optimized parameters documented

### Dependencies
- Phase 1 complete (need historical data)
- Technical indicators working

### Timeline: Week 3

### Success Criteria
- ✓ Strategy shows positive expected value
- ✓ Sharpe ratio > 1.5 on backtest
- ✓ Consistent profits across different periods
- ✓ Understand when strategy works/doesn't work

---

## ⏳ Phase 3: Risk Management + Order Execution (Week 4)

### Goals
- Implement position sizing for micro-capital
- Build stop loss management
- Integrate with Angel One API for orders
- Test order placement (paper mode)

### Tasks

#### 3.1 Position Sizing
- [ ] Create `src/risk/position_sizer.py`
- [ ] Implement fixed amount method (₹1,000-2,000 per trade)
- [ ] Calculate max lots based on premium
- [ ] Verify within capital limits
- [ ] **Estimated Time:** 2 hours

#### 3.2 Stop Loss Manager
- [ ] Create `src/risk/stop_loss_manager.py`
- [ ] Fixed stop loss (% of premium)
- [ ] Trailing stop loss logic
- [ ] Move to breakeven logic
- [ ] Dynamic adjustment based on P&L
- [ ] **Estimated Time:** 3-4 hours

#### 3.3 Risk Limits
- [ ] Create `src/risk/risk_manager.py`
- [ ] Daily loss limit (₹500)
- [ ] Weekly loss limit (₹1,000)
- [ ] Max positions (2)
- [ ] Circuit breaker logic
- [ ] **Estimated Time:** 2-3 hours

#### 3.4 Order Execution
- [ ] Create `src/execution/order_manager.py`
- [ ] Place market order via Angel One API
- [ ] Place limit order
- [ ] Place stop loss order
- [ ] Order status tracking
- [ ] Handle API errors and retries
- [ ] **Estimated Time:** 4-5 hours

#### 3.5 Paper Trading Mode
- [ ] Create `src/execution/paper_trader.py`
- [ ] Simulate order execution
- [ ] Use real market prices
- [ ] Track paper portfolio
- [ ] Log all trades
- [ ] **Estimated Time:** 3-4 hours

### Deliverables
- [ ] Position sizing working for ₹10K capital
- [ ] Stop loss management tested
- [ ] Order placement via Angel One API working
- [ ] Paper trading mode functional
- [ ] Risk limits enforced

### Dependencies
- Angel One API credentials (must have by now)
- Phase 1 complete (real-time data)
- Phase 2 complete (strategy)

### Timeline: Week 4

### Success Criteria
- ✓ Can place orders via API successfully
- ✓ Stop losses execute correctly
- ✓ Risk limits prevent over-trading
- ✓ Paper trading tracks P&L accurately

---

## ⏳ Phase 4: Paper Trading (Week 5)

### Goals
- Run system in paper mode for 1 week minimum
- Test all components together
- Monitor and fix bugs
- Verify strategy performance

### Tasks

#### 4.1 Portfolio Tracking
- [ ] Create `src/portfolio/portfolio_tracker.py`
- [ ] Track open positions
- [ ] Calculate real-time P&L
- [ ] Track Greeks for options
- [ ] Monitor margin usage
- [ ] **Estimated Time:** 3-4 hours

#### 4.2 Telegram Notifications
- [ ] Create `src/utils/telegram_notifier.py`
- [ ] Set up Telegram bot
- [ ] Trade entry notifications
- [ ] Trade exit notifications
- [ ] Daily summary
- [ ] Risk alerts
- [ ] **Estimated Time:** 2-3 hours

#### 4.3 Main Trading System
- [ ] Create `src/main.py`
- [ ] System startup sequence
- [ ] Pre-market analysis
- [ ] Market hours monitoring
- [ ] Strategy signal generation
- [ ] Order execution flow
- [ ] End-of-day procedures
- [ ] **Estimated Time:** 5-6 hours

#### 4.4 Scheduler
- [ ] Create `src/utils/scheduler.py`
- [ ] Start at 8:45 AM
- [ ] Market hours: 9:15 AM - 3:30 PM
- [ ] Stop at 3:30 PM
- [ ] Run only on trading days
- [ ] **Estimated Time:** 2-3 hours

#### 4.5 Testing & Validation
- [ ] Run paper trading for 5 days minimum
- [ ] Log all signals and trades
- [ ] Monitor for errors
- [ ] Verify P&L calculations
- [ ] Compare with manual calculations
- [ ] Fix any bugs found
- [ ] **Estimated Time:** 5-10 hours (monitoring)

### Deliverables
- [ ] Complete trading system running autonomously
- [ ] Paper trades logged for 1 week
- [ ] Telegram notifications working
- [ ] No critical bugs
- [ ] P&L tracking accurate

### Dependencies
- All previous phases complete
- Telegram bot token
- 1 week of live market data

### Timeline: Week 5 (5 trading days minimum)

### Success Criteria
- ✓ System runs without crashes for 1 week
- ✓ All trades logged correctly
- ✓ Notifications timely and accurate
- ✓ Paper P&L matches expectations
- ✓ Ready for live trading

---

## ⏳ Phase 5: Live Trading - Conservative Start (Week 6+)

### Goals
- Start live trading with ₹5,000 only
- Take max 1 trade per day
- Monitor closely
- Build confidence

### Tasks

#### 5.1 Pre-Live Checklist
- [ ] Review all paper trading results
- [ ] Verify Angel One account has ₹5,000
- [ ] Activate F&O segment
- [ ] Test live order placement (₹100 trade)
- [ ] Verify Telegram alerts working
- [ ] Set risk limits in config (₹250 daily loss for ₹5K)
- [ ] **Estimated Time:** 2-3 hours

#### 5.2 Go Live
- [ ] Switch config mode from 'paper' to 'live'
- [ ] Start with 1 trade per day max
- [ ] Monitor every trade manually
- [ ] Keep detailed notes
- [ ] **Estimated Time:** Daily monitoring

#### 5.3 Week 1 Live Trading
- [ ] Day 1: First live trade (monitor closely)
- [ ] Day 2-5: Continue with 1 trade/day
- [ ] Daily review and journaling
- [ ] Track emotional responses
- [ ] **Estimated Time:** 1-2 hours/day

#### 5.4 Performance Review
- [ ] After Week 1: Comprehensive review
- [ ] Calculate win rate
- [ ] Calculate average P&L
- [ ] Compare with backtesting
- [ ] Identify any issues
- [ ] **Estimated Time:** 2-3 hours

#### 5.5 Decision Point
- [ ] If profitable: Continue and possibly increase to 2 trades/day
- [ ] If breakeven: Continue for another week
- [ ] If losing: Stop, analyze, fix issues, return to paper trading
- [ ] **Estimated Time:** 1 hour

### Deliverables
- [ ] 5 days (1 week) of live trading data
- [ ] All trades documented
- [ ] Performance metrics calculated
- [ ] Decision made on continuing

### Dependencies
- Phase 4 complete (successful paper trading)
- ₹5,000 in Angel One account
- Mental preparedness

### Timeline: Week 6 (then ongoing)

### Success Criteria
- ✓ No major losses (capital preserved)
- ✓ System executes trades as expected
- ✓ Win rate > 40% (acceptable for start)
- ✓ Confidence in system growing

---

## ⏳ Phase 6: Optimization & Scaling (Month 2+)

### Goals
- Optimize based on live results
- Scale capital if profitable
- Add second strategy
- Continuous improvement

### Tasks

#### 6.1 Live Performance Analysis
- [ ] Analyze all live trades
- [ ] Identify what's working
- [ ] Identify what's not working
- [ ] Compare with backtesting
- [ ] **Ongoing**

#### 6.2 Strategy Refinement
- [ ] Adjust parameters based on live data
- [ ] Disable underperforming setups
- [ ] Focus on high-probability setups
- [ ] **Ongoing**

#### 6.3 Capital Scaling
- [ ] Month 1 live: ₹5,000
- [ ] If profitable Month 2: Add ₹5,000 → Total ₹10,000
- [ ] If profitable Month 3: Add ₹10,000 → Total ₹20,000
- [ ] Month 6: Add ₹30,000 → Total ₹50,000
- [ ] **Gradual over 6 months**

#### 6.4 Add Second Strategy
- [ ] Implement mean reversion strategy
- [ ] Backtest separately
- [ ] Paper trade for 1 week
- [ ] Add to live system
- [ ] **Month 3-4**

#### 6.5 Advanced Features
- [ ] Better market regime detection
- [ ] Multiple timeframe analysis
- [ ] Options Greeks-based adjustments
- [ ] Machine learning for signal filtering (optional)
- [ ] **Month 4+**

### Deliverables
- [ ] Consistent monthly profits
- [ ] Capital scaled to ₹50K+
- [ ] Multiple strategies running
- [ ] System fully autonomous

### Timeline: Months 2-6

### Success Criteria
- ✓ Monthly returns: 8-20%
- ✓ Sharpe ratio > 1.0 in live trading
- ✓ Max drawdown < 10%
- ✓ System runs independently
- ✓ You just check Telegram summaries

---

## Modified Timeline (Accelerated for Micro-Capital)

```
Week 1:  ✅ Phase 0 - Setup COMPLETE
Week 2:  ⏳ Phase 1 - Data Pipeline IN PROGRESS
Week 3:     Phase 2 - First Strategy + Backtesting
Week 4:     Phase 3 - Risk + Execution
Week 5:     Phase 4 - Paper Trading
Week 6:     Phase 5 - Go Live with ₹5K!
Month 2-6:  Phase 6 - Optimize & Scale to ₹50K
```

**Total time to live trading: 6 weeks** (vs original 6 months)

This is realistic for micro-capital because:
- Simpler strategies (just options buying)
- Fewer positions (max 2)
- Less infrastructure needed
- Can iterate faster with small capital

---

## Current Status

**Phase 0:** ✅ COMPLETE
- Python environment ready
- All dependencies installed
- Utility modules working
- Configuration ready
- Waiting for Angel One API credentials

**Phase 1:** ⏳ STARTED
- **Can start now:** Market calendar (no API needed)
- **Blocked:** Historical data, real-time data (need API)
- **ETA:** 2-3 days once API credentials arrive

**Next Action:** Start building market calendar module while waiting for Angel One API

---

## Key Differences from Original Plan

### Original (Large Capital)
- 10 phases
- 6 months timeline
- Complex risk management
- Multiple strategies from start
- Extensive testing

### Micro-Capital (Optimized)
- 6 phases (consolidated)
- 6 weeks to live trading
- Simplified risk (options buying only)
- One strategy first, add more later
- Faster iteration

**Philosophy:** Learn by doing with small capital, scale when proven

---

**Last Updated:** 2025-11-18
**Current Phase:** Phase 1 - Data Pipeline
**Next Milestone:** Market calendar working (2-3 hours)
**Blocker:** Angel One API credentials (ETA: 2-3 days)
