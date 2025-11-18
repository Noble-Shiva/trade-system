# Automated F&O Trading System

An intelligent, automated trading system for Indian Futures & Options markets (BSE/NSE) with backtesting, risk management, and multi-strategy support.

## Overview

This system automates F&O trading operations using proven strategies, dynamic risk management, and comprehensive backtesting. It's designed to:

- 📊 **Automate Trading:** Execute trades automatically during market hours
- 🎯 **Multi-Strategy:** Support multiple trading strategies (momentum, mean reversion, volatility-based)
- 🛡️ **Risk Management:** Dynamic stop losses, position sizing, portfolio limits
- 📈 **Backtesting:** Extensive historical testing before live deployment
- 🔔 **Notifications:** Real-time alerts via Telegram
- 💰 **Conservative Start:** Begin with low-investment options, scale gradually

## Quick Links

- **[⭐ Micro-Capital Plan (₹5K-₹10K)](./MICRO_CAPITAL_PLAN.md)** - **START HERE!** Optimized plan for small capital
- **[Complete Plan & Documentation](./TRADING_SYSTEM_PLAN.md)** - Comprehensive 14,000+ word plan covering everything
- **[Implementation Roadmap](#implementation-roadmap)** - Phase-by-phase development guide
- **[Getting Started](#getting-started)** - Setup instructions

## Features

### Core Capabilities

- ✅ Real-time market data ingestion (NSE/BSE)
- ✅ Historical data management (5+ years)
- ✅ Multiple trading strategies with automatic selection
- ✅ Options Greeks calculation (Delta, Gamma, Theta, Vega)
- ✅ Dynamic trailing stop losses
- ✅ Position sizing and risk management
- ✅ Portfolio tracking and P&L monitoring
- ✅ Comprehensive backtesting framework
- ✅ Paper trading mode
- ✅ Live trading with multiple broker support

### Supported Brokers

- **Zerodha Kite Connect** (Recommended for production)
- **Upstox API**
- **Angel One Smart API** (Free - good for development)
- **Dhan API**
- **Fyers API**

## System Architecture

```
Data Ingestion → Strategy Engine → Risk Management → Order Execution
       ↓               ↓                  ↓                ↓
  Market Data    Signal Generation   Stop Loss      Broker API
  Historical     Multi-Strategy      Position Size  Order Tracking
  Real-time      Greeks Calc        Portfolio Risk   Fill Monitoring
                                                          ↓
                                                  Portfolio & P&L
                                                  Notifications
                                                  Backtesting
```

## Trading Strategies Included

1. **Momentum Trading** - Trend following using moving averages and breakouts
2. **Mean Reversion** - Profit from price returning to average (RSI, Bollinger Bands)
3. **Volatility Breakout** - Capture moves during high VIX periods
4. **Delta-Neutral** - Options strategies (Iron Condor, Straddles, Strangles)
5. **Premium Collection** - Theta decay strategies for range-bound markets
6. **Arbitrage** - Statistical arbitrage on correlated assets

## Technology Stack

- **Language:** Python 3.11+
- **Backtesting:** backtesting.py, backtrader
- **Data:** jugaad-data, nsepython, broker APIs
- **Technical Analysis:** ta-lib, pandas-ta
- **Database:** PostgreSQL, InfluxDB (time-series)
- **Notifications:** Telegram Bot API
- **Charting:** TradingView Lightweight Charts, mplfinance
- **Deployment:** Docker, Cloud VPS

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Trading account with broker (Zerodha/Upstox/Angel One)
- API access from broker
- Basic understanding of F&O trading

### Installation

```bash
# Clone repository
git clone https://github.com/Noble-Shiva/trade-system.git
cd trade-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your broker API credentials
```

### Quick Start

```bash
# Download historical data
python src/data/download_historical.py

# Run backtesting
python src/backtesting/run_backtest.py --strategy momentum

# Start paper trading
python src/main.py --mode paper

# Start live trading (after successful paper trading)
python src/main.py --mode live
```

## Implementation Roadmap

### Phase 0: Setup & Infrastructure (Week 1-2)
- ✅ Development environment
- ✅ Project structure
- ✅ Broker API credentials
- ✅ Database setup

### Phase 1: Data Pipeline (Week 3-4)
- Historical data downloader
- Real-time data streaming
- Market calendar integration
- Data quality checks

### Phase 2: Backtesting Framework (Week 5-7)
- Backtesting.py setup
- Strategy implementation
- Performance metrics
- Optimization pipeline

### Phase 3: Strategy Implementation (Week 8-10)
- Core strategies (4+)
- Strategy selector
- Signal generation
- Greeks calculator

### Phase 4: Risk Management (Week 11-12)
- Position sizing
- Dynamic stop losses
- Portfolio limits
- Circuit breakers

### Phase 5: Order Execution (Week 13-14)
- Broker integration
- Order management
- Execution monitoring
- Paper trading mode

### Phase 6: Portfolio Management (Week 15-16)
- Position tracking
- P&L calculator
- Performance analytics
- Dashboard

### Phase 7: Notifications & Monitoring (Week 17)
- Telegram bot
- Logging system
- System monitoring
- Audit trail

### Phase 8: Paper Trading (Week 18-22)
- 1 month paper trading
- System validation
- Bug fixes
- Documentation

### Phase 9: Live Trading - Conservative (Week 23-26)
- Start with ₹50k-₹1L
- 2% per trade max
- Daily monitoring
- Build confidence

### Phase 10: Scaling (Month 2-3+)
- Analyze results
- Scale capital
- Add strategies
- Continuous improvement

## Risk Management

### Position Level
- Maximum 2% capital per trade
- ATR-based stop losses
- Trailing stops for profit protection
- 2:1 or 3:1 reward-to-risk targets

### Portfolio Level
- Maximum 5% daily loss limit
- 15% maximum drawdown
- Position concentration limits
- Diversification across strategies

### System Safeguards
- Heartbeat monitoring
- Automatic error handling
- Manual kill switch
- Daily reconciliation

## Key Performance Targets

- **Sharpe Ratio:** > 1.5
- **Sortino Ratio:** > 2.0
- **Maximum Drawdown:** < 20%
- **Win Rate:** > 50%
- **Profit Factor:** > 1.5
- **Annual Return:** 15-30% (conservative), 30-50% (good), 50%+ (exceptional)

## Project Structure

```
trade-system/
├── src/
│   ├── data/              # Data ingestion and storage
│   ├── strategies/        # Trading strategies
│   ├── execution/         # Order execution
│   ├── risk/              # Risk management
│   ├── backtesting/       # Backtesting engine
│   ├── portfolio/         # Portfolio tracking
│   ├── utils/             # Utilities
│   └── main.py            # Main entry point
├── tests/                 # Unit tests
├── data/                  # Historical data storage
├── logs/                  # Log files
├── config/                # Configuration files
├── docs/                  # Documentation
├── TRADING_SYSTEM_PLAN.md # Complete plan (READ THIS FIRST!)
├── requirements.txt       # Dependencies
└── README.md              # This file
```

## Documentation

- **[Complete Plan](./TRADING_SYSTEM_PLAN.md)** - Everything you need to know
- **[Strategy Guide](./docs/strategies.md)** - Strategy details and parameters
- **[Risk Management](./docs/risk_management.md)** - Risk controls and limits
- **[API Integration](./docs/api_integration.md)** - Broker API setup
- **[Backtesting Guide](./docs/backtesting.md)** - How to backtest strategies

## Important Warnings

⚠️ **F&O trading is highly risky**
- Only trade with capital you can afford to lose
- Past performance does not guarantee future results
- Start small, scale gradually
- Keep strict risk limits

⚠️ **System Risks**
- Software bugs can cause unexpected behavior
- API failures can lead to missed opportunities
- Internet downtime can prevent trading
- Always have backup plans

⚠️ **Regulatory Compliance**
- SEBI requires algo trading approval from brokers
- Maintain audit trails for all trades
- F&O profits are taxable as business income
- Consult with tax advisor

## Budget Estimate

### Development Phase (4 months)
- API costs: ₹0 - ₹8,000 (Free with Angel One, ₹2k/mo with Zerodha)
- VPS: ₹8,000 - ₹20,000
- **Total:** ₹8,000 - ₹28,000

### Live Trading
- Monthly operational: ₹4,000 - ₹7,000
- Initial trading capital: ₹50,000 - ₹1,00,000 (separate from operational)

## Success Criteria

### Backtesting
- ✓ Sharpe ratio > 1.5 for at least 2 strategies
- ✓ Max drawdown < 20%
- ✓ Profitable over 3+ years

### Paper Trading
- ✓ 1 month without crashes
- ✓ All orders execute correctly
- ✓ Performance close to backtesting

### Live Trading
- ✓ Month 1: Capital preservation, no major losses
- ✓ Month 2-3: Positive returns, Sharpe > 1.0, ready to scale

## Contributing

This is a personal trading system. If you fork it:
1. Test extensively before using real money
2. Understand all strategies and risk controls
3. Start with paper trading
4. Use small capital initially

## License

Private project. Not for commercial distribution.

## Disclaimer

This software is for educational purposes. Trading F&O involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this system. Always do your own research and consult with financial advisors.

## Support & Resources

- **Issues:** [GitHub Issues](https://github.com/Noble-Shiva/trade-system/issues)
- **NSE Academy:** https://www.nseindia.com/learn
- **QuantInsti:** https://www.quantinsti.com/
- **Zerodha Varsity:** https://zerodha.com/varsity/

## Acknowledgments

- NSE/BSE for market data access
- Broker APIs (Zerodha, Upstox, Angel One)
- Open source trading community
- Python trading libraries ecosystem

---

**Status:** Planning & Design Phase Complete ✅
**Next:** Phase 0 - Setup & Infrastructure
**Timeline:** 6 months to live trading
**Risk Level:** High - F&O Trading
**Recommended Capital:** Start with ₹50,000 - ₹1,00,000

**Last Updated:** 2025-11-18
