#!/usr/bin/env python3
"""
Backtest Runner - Run backtests on historical data
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from loguru import logger
from datetime import datetime

from src.backtest import (
    HistoricalDataLoader,
    BacktestEngine,
    BacktestVisualizer
)


def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )


def load_config(config_path: str) -> dict:
    """Load configuration from YAML"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def download_data(args, config):
    """Download historical data"""
    loader = HistoricalDataLoader(config.get("backtest", {}).get("data_path", "data/historical"))

    print(f"\nDownloading data for {args.symbol}...")
    print(f"Period: {args.start_date} to {args.end_date}")

    # Download index data
    index_data = loader.download_index_data(
        args.symbol,
        args.start_date,
        args.end_date
    )
    print(f"Downloaded {len(index_data)} days of index data")

    # Generate synthetic option data
    print("\nGenerating synthetic option data...")
    option_data = loader.generate_synthetic_option_data(
        index_data,
        args.symbol,
        strike_interval=50 if args.symbol in ['NIFTY', 'BANKNIFTY'] else 100,
        num_strikes=30
    )
    print(f"Generated {len(option_data)} option records")

    print("\nData download complete!")


def run_backtest(args, config):
    """Run backtest"""
    # Merge config with backtest settings
    backtest_config = {
        "initial_capital": args.capital or config.get("backtest", {}).get("initial_capital", 100000),
        "commission": config.get("backtest", {}).get("commission", 20),
        "slippage_pct": 0.1,
        "data_path": config.get("backtest", {}).get("data_path", "data/historical"),
        "risk": config.get("risk", {}),
        "stop_loss": config.get("stop_loss", {}),
        "strategies": config.get("strategies", {})
    }

    print("\n" + "=" * 60)
    print("BACKTEST CONFIGURATION")
    print("=" * 60)
    print(f"Symbol: {args.symbol}")
    print(f"Strategy: {args.strategy}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Initial Capital: ₹{backtest_config['initial_capital']:,.0f}")
    print("=" * 60)

    # Run backtest
    engine = BacktestEngine(backtest_config)

    try:
        result = engine.run(
            symbol=args.symbol,
            strategy_name=args.strategy,
            start_date=args.start_date,
            end_date=args.end_date
        )
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease download data first:")
        print(f"  python scripts/run_backtest.py download --symbol {args.symbol} --start-date {args.start_date} --end-date {args.end_date}")
        sys.exit(1)

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Final Capital: ₹{result.final_capital:,.0f}")
    print(f"Total Return: ₹{result.total_return:,.0f} ({result.total_return_pct:+.2f}%)")
    print("-" * 60)
    print(f"Total Trades: {result.total_trades}")
    print(f"Win Rate: {result.win_rate:.1f}%")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown_pct:.1f}%")
    print("-" * 60)
    print(f"Average Win: ₹{result.avg_win:,.0f}")
    print(f"Average Loss: ₹{result.avg_loss:,.0f}")
    print("=" * 60)

    # Check if meets criteria
    from src.backtest.metrics import PerformanceMetrics
    metrics = PerformanceMetrics(result.trades, result.initial_capital, result.daily_returns)
    passes, failures = metrics.meets_criteria(
        min_win_rate=50,
        min_profit_factor=1.3,
        min_sharpe=0.8,
        max_drawdown_pct=15
    )

    print("\nCRITERIA CHECK:")
    if passes:
        print("✅ Strategy PASSES minimum criteria")
        print("   Ready for paper trading!")
    else:
        print("❌ Strategy FAILS minimum criteria:")
        for f in failures:
            print(f"   - {f}")

    # Generate report
    if not args.no_report:
        print("\nGenerating report...")
        visualizer = BacktestVisualizer(result)

        # Generate both text and HTML reports
        text_report = visualizer.generate_text_report()
        print(f"Text report: {text_report}")

        try:
            html_report = visualizer.generate_report()
            print(f"HTML report: {html_report}")
        except Exception as e:
            logger.debug(f"Could not generate HTML report: {e}")

        # Save trades CSV
        csv_file = visualizer.save_trades_csv()
        if csv_file:
            print(f"Trade log: {csv_file}")

    return result


def compare_strategies(args, config):
    """Compare multiple strategies"""
    strategies = args.strategies.split(',')

    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)
    print(f"Symbol: {args.symbol}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Strategies: {', '.join(strategies)}")
    print("=" * 60)

    results = {}

    for strategy in strategies:
        strategy = strategy.strip()
        print(f"\nRunning {strategy}...")

        backtest_config = {
            "initial_capital": args.capital or config.get("backtest", {}).get("initial_capital", 100000),
            "commission": config.get("backtest", {}).get("commission", 20),
            "slippage_pct": 0.1,
            "data_path": config.get("backtest", {}).get("data_path", "data/historical"),
            "risk": config.get("risk", {}),
            "stop_loss": config.get("stop_loss", {}),
            "strategies": config.get("strategies", {})
        }

        engine = BacktestEngine(backtest_config)

        try:
            result = engine.run(
                symbol=args.symbol,
                strategy_name=strategy,
                start_date=args.start_date,
                end_date=args.end_date
            )
            results[strategy] = result
        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Print comparison table
    if results:
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)
        print(f"{'Strategy':<20} {'Return %':>10} {'Win Rate':>10} {'Sharpe':>10} {'Max DD':>10} {'Trades':>8}")
        print("-" * 80)

        for name, result in results.items():
            print(f"{name:<20} {result.total_return_pct:>+9.1f}% {result.win_rate:>9.1f}% "
                  f"{result.sharpe_ratio:>10.2f} {result.max_drawdown_pct:>9.1f}% {result.total_trades:>8}")

        print("=" * 80)

        # Recommend best strategy
        best = max(results.items(), key=lambda x: x[1].sharpe_ratio)
        print(f"\nBest strategy by Sharpe Ratio: {best[0]}")


def main():
    parser = argparse.ArgumentParser(
        description="BSE F&O Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download historical data
  python scripts/run_backtest.py download --symbol NIFTY --start-date 2023-01-01 --end-date 2024-01-01

  # Run single strategy backtest
  python scripts/run_backtest.py run --symbol NIFTY --strategy bull_put_spread --start-date 2023-01-01 --end-date 2024-01-01

  # Compare multiple strategies
  python scripts/run_backtest.py compare --symbol NIFTY --strategies "iron_condor,bull_put_spread" --start-date 2023-01-01 --end-date 2024-01-01
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download historical data')
    download_parser.add_argument('--symbol', required=True, help='Symbol (NIFTY, BANKNIFTY)')
    download_parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    download_parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run backtest')
    run_parser.add_argument('--symbol', required=True, help='Symbol')
    run_parser.add_argument('--strategy', required=True, help='Strategy name')
    run_parser.add_argument('--start-date', required=True, help='Start date')
    run_parser.add_argument('--end-date', required=True, help='End date')
    run_parser.add_argument('--capital', type=float, help='Initial capital')
    run_parser.add_argument('--no-report', action='store_true', help='Skip report generation')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare strategies')
    compare_parser.add_argument('--symbol', required=True, help='Symbol')
    compare_parser.add_argument('--strategies', required=True, help='Comma-separated strategies')
    compare_parser.add_argument('--start-date', required=True, help='Start date')
    compare_parser.add_argument('--end-date', required=True, help='End date')
    compare_parser.add_argument('--capital', type=float, help='Initial capital')

    # Common arguments
    parser.add_argument('--config', default='config/settings.yaml', help='Config file')
    parser.add_argument('--log-level', default='INFO', help='Log level')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup
    setup_logging(args.log_level)
    config = load_config(args.config)

    # Execute command
    if args.command == 'download':
        download_data(args, config)
    elif args.command == 'run':
        run_backtest(args, config)
    elif args.command == 'compare':
        compare_strategies(args, config)


if __name__ == "__main__":
    main()
