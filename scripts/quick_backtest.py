#!/usr/bin/env python3
"""
=============================================================================
COMPLETE BACKTESTING SCRIPT - BSE F&O Trading System
=============================================================================

This script runs a complete backtest workflow in one go:
1. Downloads historical data (if not present)
2. Generates synthetic option data
3. Runs backtests for all strategies
4. Compares performance
5. Generates detailed reports

USAGE:
------
# Run with defaults (NIFTY, last 1 year, ₹10,000 capital)
python scripts/quick_backtest.py

# Custom parameters
python scripts/quick_backtest.py --symbol BANKNIFTY --capital 25000 --months 6

# Quick test (last 3 months only)
python scripts/quick_backtest.py --quick

WHAT THIS SCRIPT DOES:
----------------------
✓ Downloads NIFTY/BANKNIFTY historical data
✓ Generates synthetic option prices
✓ Tests all 3 strategies (Iron Condor, Bull Put, Bear Call)
✓ Calculates performance metrics (Win Rate, Sharpe, Drawdown)
✓ Generates HTML + Text reports
✓ Shows which strategy is best
✓ Tells you if ready for paper trading

OUTPUT:
-------
- data/historical/           # Downloaded data
- data/backtest_results/     # Reports and charts
- Console output with summary

REQUIREMENTS:
-------------
- config/settings.yaml must exist
- Internet connection for data download
- pip install -r requirements.txt

IMPORTANT NOTES:
----------------
⚠️  Uses SYNTHETIC option data (not real historical data)
⚠️  Real option data requires paid subscription
⚠️  Synthetic data is good for testing logic, not exact prices
✅  Real broker integration will use live data

Ready for live trading when:
- Win Rate > 50%
- Profit Factor > 1.3
- Sharpe Ratio > 0.8
- Max Drawdown < 15%

=============================================================================
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from loguru import logger

from src.backtest import (
    HistoricalDataLoader,
    BacktestEngine,
    BacktestVisualizer,
    PerformanceMetrics
)


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_SYMBOL = "NIFTY"
DEFAULT_CAPITAL = 10000
DEFAULT_MONTHS_BACK = 12  # 1 year
QUICK_TEST_MONTHS = 3     # For quick testing

STRATEGIES = [
    "iron_condor",
    "bull_put_spread",
    "bear_call_spread"
]

# Success criteria for live trading
CRITERIA = {
    "min_win_rate": 50,
    "min_profit_factor": 1.3,
    "min_sharpe": 0.8,
    "max_drawdown_pct": 15
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step: int, total: int, text: str):
    """Print step number"""
    print(f"\n[{step}/{total}] {text}")
    print("-" * 70)


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"⚠️  {text}")


def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")


def calculate_dates(months_back: int) -> tuple[str, str]:
    """Calculate start and end dates"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)

    return (
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )


def load_config() -> dict:
    """Load configuration from YAML"""
    config_path = project_root / "config" / "settings.yaml"

    if not config_path.exists():
        print_error(f"Config file not found: {config_path}")
        print("Please create config/settings.yaml first")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


# ============================================================================
# MAIN WORKFLOW STEPS
# ============================================================================

def step_1_download_data(
    loader: HistoricalDataLoader,
    symbol: str,
    start_date: str,
    end_date: str
) -> bool:
    """Step 1: Download historical data"""
    print_step(1, 5, "Downloading Historical Data")

    print(f"Symbol: {symbol}")
    print(f"Period: {start_date} to {end_date}")

    try:
        # Check if data already exists
        try:
            existing = loader.load_index_data(symbol)
            print_success(f"Found existing data: {len(existing)} days")

            # Check if we need to update
            existing_start = existing['date'].min().strftime("%Y-%m-%d")
            existing_end = existing['date'].max().strftime("%Y-%m-%d")

            if existing_start <= start_date and existing_end >= end_date:
                print_success("Data covers required period, skipping download")
                return True
        except FileNotFoundError:
            pass

        # Download data
        print("Downloading from NSE/Yahoo Finance...")
        index_data = loader.download_index_data(symbol, start_date, end_date)
        print_success(f"Downloaded {len(index_data)} days of index data")

        return True

    except Exception as e:
        print_error(f"Failed to download data: {e}")
        return False


def step_2_generate_options(
    loader: HistoricalDataLoader,
    symbol: str
) -> bool:
    """Step 2: Generate synthetic option data"""
    print_step(2, 5, "Generating Synthetic Option Data")

    try:
        # Load index data
        index_data = loader.load_index_data(symbol)

        # Check if option data exists
        try:
            existing_options = loader.load_option_data(symbol)
            if len(existing_options) > 0:
                print_success(f"Found existing option data: {len(existing_options)} records")
                return True
        except FileNotFoundError:
            pass

        # Generate option data
        print("Generating option prices (this may take a minute)...")

        strike_interval = 50 if symbol in ['NIFTY', 'BANKNIFTY'] else 100

        option_data = loader.generate_synthetic_option_data(
            index_data,
            symbol,
            strike_interval=strike_interval,
            num_strikes=30
        )

        print_success(f"Generated {len(option_data)} option records")

        # Show sample
        print("\nSample option data:")
        sample = option_data.head(3)
        for _, row in sample.iterrows():
            print(f"  {row['date'].strftime('%Y-%m-%d')} | "
                  f"Strike: {row['strike']:.0f} | "
                  f"CE: ₹{row['call_price']:.0f} | "
                  f"PE: ₹{row['put_price']:.0f}")

        return True

    except Exception as e:
        print_error(f"Failed to generate option data: {e}")
        return False


def step_3_run_backtests(
    config: dict,
    symbol: str,
    start_date: str,
    end_date: str,
    capital: float
) -> dict:
    """Step 3: Run backtests for all strategies"""
    print_step(3, 5, "Running Backtests for All Strategies")

    results = {}

    # Prepare backtest config
    backtest_config = {
        "initial_capital": capital,
        "commission": config.get("backtest", {}).get("commission", 20),
        "slippage_pct": 0.1,
        "data_path": config.get("backtest", {}).get("data_path", "data/historical"),
        "risk": config.get("risk", {}),
        "stop_loss": config.get("stop_loss", {}),
        "strategies": config.get("strategies", {})
    }

    engine = BacktestEngine(backtest_config)

    for i, strategy in enumerate(STRATEGIES, 1):
        print(f"\n[{i}/{len(STRATEGIES)}] Testing: {strategy.replace('_', ' ').title()}")
        print("  " + "-" * 60)

        try:
            result = engine.run(
                symbol=symbol,
                strategy_name=strategy,
                start_date=start_date,
                end_date=end_date
            )

            results[strategy] = result

            # Print quick summary
            print(f"  Return: {result.total_return_pct:+.1f}% | "
                  f"Win Rate: {result.win_rate:.0f}% | "
                  f"Trades: {result.total_trades} | "
                  f"Sharpe: {result.sharpe_ratio:.2f}")

        except Exception as e:
            print_error(f"  Failed: {e}")
            continue

    if not results:
        print_error("No successful backtests!")
        return {}

    print_success(f"\nCompleted {len(results)} strategy backtests")
    return results


def step_4_compare_strategies(results: dict):
    """Step 4: Compare all strategies"""
    print_step(4, 5, "Strategy Comparison")

    if not results:
        print_warning("No results to compare")
        return

    # Print comparison table
    print("\n" + "=" * 100)
    print(f"{'Strategy':<25} {'Return %':>10} {'Win Rate':>10} {'Sharpe':>10} "
          f"{'Max DD':>10} {'Trades':>8} {'Status':>10}")
    print("-" * 100)

    best_sharpe = None
    best_sharpe_name = None

    for name, result in results.items():
        # Check if meets criteria
        metrics = PerformanceMetrics(result.trades, result.initial_capital, result.daily_returns)
        passes, failures = metrics.meets_criteria(
            min_win_rate=CRITERIA["min_win_rate"],
            min_profit_factor=CRITERIA["min_profit_factor"],
            min_sharpe=CRITERIA["min_sharpe"],
            max_drawdown_pct=CRITERIA["max_drawdown_pct"]
        )

        status = "✅ PASS" if passes else "❌ FAIL"

        print(f"{name.replace('_', ' ').title():<25} "
              f"{result.total_return_pct:>+9.1f}% "
              f"{result.win_rate:>9.1f}% "
              f"{result.sharpe_ratio:>10.2f} "
              f"{result.max_drawdown_pct:>9.1f}% "
              f"{result.total_trades:>8} "
              f"{status:>10}")

        # Track best
        if best_sharpe is None or result.sharpe_ratio > best_sharpe:
            best_sharpe = result.sharpe_ratio
            best_sharpe_name = name

    print("=" * 100)

    # Recommend best
    if best_sharpe_name:
        print(f"\n🏆 Best Strategy (by Sharpe Ratio): {best_sharpe_name.replace('_', ' ').title()}")
        best_result = results[best_sharpe_name]

        # Check if ready for live trading
        metrics = PerformanceMetrics(
            best_result.trades,
            best_result.initial_capital,
            best_result.daily_returns
        )
        passes, failures = metrics.meets_criteria(
            min_win_rate=CRITERIA["min_win_rate"],
            min_profit_factor=CRITERIA["min_profit_factor"],
            min_sharpe=CRITERIA["min_sharpe"],
            max_drawdown_pct=CRITERIA["max_drawdown_pct"]
        )

        if passes:
            print("\n" + "🎉" * 30)
            print("✅ READY FOR PAPER TRADING!")
            print("🎉" * 30)
            print("\nNext steps:")
            print("1. Run paper trading for 2-4 weeks")
            print("2. Verify performance matches backtest")
            print("3. Start live trading with minimum capital")
        else:
            print("\n⚠️  NOT READY FOR LIVE TRADING")
            print("\nIssues found:")
            for failure in failures:
                print(f"  ❌ {failure}")
            print("\nRecommendations:")
            print("  1. Adjust strategy parameters in config/settings.yaml")
            print("  2. Try longer backtest period")
            print("  3. Consider different market conditions")


def step_5_generate_reports(results: dict, symbol: str, start_date: str, end_date: str):
    """Step 5: Generate detailed reports"""
    print_step(5, 5, "Generating Reports")

    if not results:
        print_warning("No results to report")
        return

    report_dir = project_root / "data" / "backtest_results"
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating reports in: {report_dir}")

    for strategy_name, result in results.items():
        print(f"\n  {strategy_name.replace('_', ' ').title()}:")

        visualizer = BacktestVisualizer(result, output_dir=str(report_dir))

        # Generate text report
        text_file = visualizer.generate_text_report(
            filename=f"{strategy_name}_{symbol}_{start_date}_{end_date}.txt"
        )
        print(f"    📄 Text: {Path(text_file).name}")

        # Generate HTML report (if plotly available)
        try:
            html_file = visualizer.generate_report(
                filename=f"{strategy_name}_{symbol}_{start_date}_{end_date}.html"
            )
            print(f"    📊 HTML: {Path(html_file).name}")
        except Exception as e:
            logger.debug(f"Could not generate HTML report: {e}")

        # Save trades CSV
        csv_file = visualizer.save_trades_csv(
            filename=f"{strategy_name}_{symbol}_{start_date}_{end_date}_trades.csv"
        )
        if csv_file:
            print(f"    📑 CSV:  {Path(csv_file).name}")

    print_success(f"\nAll reports saved to: {report_dir}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main backtest workflow"""

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Complete Backtesting Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: NIFTY, 1 year, ₹10,000
  python scripts/quick_backtest.py

  # Custom parameters
  python scripts/quick_backtest.py --symbol BANKNIFTY --capital 25000 --months 6

  # Quick test (3 months)
  python scripts/quick_backtest.py --quick
        """
    )

    parser.add_argument('--symbol', default=DEFAULT_SYMBOL,
                       choices=['NIFTY', 'BANKNIFTY', 'SENSEX'],
                       help=f'Symbol to backtest (default: {DEFAULT_SYMBOL})')

    parser.add_argument('--capital', type=float, default=DEFAULT_CAPITAL,
                       help=f'Initial capital in INR (default: {DEFAULT_CAPITAL})')

    parser.add_argument('--months', type=int, default=DEFAULT_MONTHS_BACK,
                       help=f'Months of history to test (default: {DEFAULT_MONTHS_BACK})')

    parser.add_argument('--quick', action='store_true',
                       help=f'Quick test with {QUICK_TEST_MONTHS} months only')

    parser.add_argument('--skip-download', action='store_true',
                       help='Skip data download (use existing data)')

    args = parser.parse_args()

    # Adjust for quick test
    if args.quick:
        args.months = QUICK_TEST_MONTHS

    # Calculate dates
    start_date, end_date = calculate_dates(args.months)

    # Print welcome banner
    print_header("BSE F&O BACKTESTING SYSTEM")
    print(f"""
Configuration:
  Symbol:        {args.symbol}
  Capital:       ₹{args.capital:,.0f}
  Period:        {start_date} to {end_date} ({args.months} months)
  Strategies:    {len(STRATEGIES)}
    """)

    if args.quick:
        print_warning("Running in QUICK TEST mode (limited history)")

    # Load config
    try:
        config = load_config()
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        return 1

    # Initialize data loader
    loader = HistoricalDataLoader(
        config.get("backtest", {}).get("data_path", "data/historical")
    )

    # Execute workflow
    try:
        # Step 1: Download data
        if not args.skip_download:
            if not step_1_download_data(loader, args.symbol, start_date, end_date):
                return 1
        else:
            print_step(1, 5, "Skipping Data Download")

        # Step 2: Generate options
        if not step_2_generate_options(loader, args.symbol):
            return 1

        # Step 3: Run backtests
        results = step_3_run_backtests(config, args.symbol, start_date, end_date, args.capital)
        if not results:
            return 1

        # Step 4: Compare strategies
        step_4_compare_strategies(results)

        # Step 5: Generate reports
        step_5_generate_reports(results, args.symbol, start_date, end_date)

        # Final message
        print_header("BACKTEST COMPLETE")
        print(f"""
✅ Successfully tested {len(results)} strategies
📊 Reports generated in data/backtest_results/
📈 Review results and decide next steps

Next Steps:
1. Review HTML reports for detailed analysis
2. Check if any strategy meets criteria for paper trading
3. Adjust parameters in config/settings.yaml if needed
4. Run paper trading before going live
        """)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception(e)
        return 1


if __name__ == "__main__":
    # Setup basic logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="WARNING",
        format="<level>{message}</level>"
    )

    sys.exit(main())
