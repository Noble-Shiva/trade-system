"""
Backtest Results Visualizer
"""

import pandas as pd
from pathlib import Path
from loguru import logger

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not installed. Visualization disabled.")


class BacktestVisualizer:
    """
    Visualize backtest results with charts and reports
    """

    def __init__(self, result, output_dir: str = "data/backtest_results"):
        self.result = result
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, filename: str = None) -> str:
        """Generate complete HTML report with charts"""
        if not PLOTLY_AVAILABLE:
            return self.generate_text_report(filename)

        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Equity Curve', 'Monthly Returns',
                'Trade P&L Distribution', 'Drawdown',
                'Win/Loss by Strategy', 'Cumulative P&L'
            ),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )

        # 1. Equity Curve
        dates = [e[0] for e in self.result.equity_curve]
        values = [e[1] for e in self.result.equity_curve]
        fig.add_trace(
            go.Scatter(x=dates, y=values, name='Equity', line=dict(color='blue')),
            row=1, col=1
        )

        # 2. Monthly Returns (if enough data)
        if len(self.result.daily_returns) > 20:
            monthly = self._calculate_monthly_returns()
            colors = ['green' if r > 0 else 'red' for r in monthly['return']]
            fig.add_trace(
                go.Bar(x=monthly['month'], y=monthly['return'], marker_color=colors, name='Monthly'),
                row=1, col=2
            )

        # 3. Trade P&L Distribution
        pnls = [t.pnl for t in self.result.trades]
        if pnls:
            fig.add_trace(
                go.Histogram(x=pnls, nbinsx=30, name='P&L Dist', marker_color='purple'),
                row=2, col=1
            )

        # 4. Drawdown
        drawdown = self._calculate_drawdown_series()
        if drawdown:
            fig.add_trace(
                go.Scatter(x=dates[:len(drawdown)], y=drawdown, fill='tozeroy',
                          name='Drawdown', line=dict(color='red')),
                row=2, col=2
            )

        # 5. Win/Loss by Strategy
        strategy_stats = self._calculate_strategy_stats()
        if strategy_stats:
            fig.add_trace(
                go.Bar(x=list(strategy_stats.keys()),
                      y=[s['wins'] for s in strategy_stats.values()],
                      name='Wins', marker_color='green'),
                row=3, col=1
            )
            fig.add_trace(
                go.Bar(x=list(strategy_stats.keys()),
                      y=[s['losses'] for s in strategy_stats.values()],
                      name='Losses', marker_color='red'),
                row=3, col=1
            )

        # 6. Cumulative P&L
        cum_pnl = self._calculate_cumulative_pnl()
        if cum_pnl:
            fig.add_trace(
                go.Scatter(x=list(range(len(cum_pnl))), y=cum_pnl,
                          name='Cumulative P&L', line=dict(color='green')),
                row=3, col=2
            )

        # Update layout
        fig.update_layout(
            height=1000,
            title_text=f"Backtest Report: {self.result.start_date} to {self.result.end_date}",
            showlegend=True
        )

        # Add metrics annotation
        metrics_text = self._get_metrics_text()
        fig.add_annotation(
            text=metrics_text,
            xref="paper", yref="paper",
            x=1.02, y=0.5,
            showarrow=False,
            font=dict(family="monospace", size=10),
            align="left",
            bordercolor="black",
            borderwidth=1
        )

        # Save
        if filename is None:
            filename = f"backtest_{self.result.start_date}_{self.result.end_date}.html"

        filepath = self.output_dir / filename
        fig.write_html(str(filepath))
        logger.info(f"Report saved to {filepath}")

        return str(filepath)

    def generate_text_report(self, filename: str = None) -> str:
        """Generate text-based report"""
        report = []
        report.append("=" * 60)
        report.append("BACKTEST REPORT")
        report.append("=" * 60)
        report.append("")
        report.append(f"Period: {self.result.start_date} to {self.result.end_date}")
        report.append(f"Initial Capital: ₹{self.result.initial_capital:,.0f}")
        report.append(f"Final Capital: ₹{self.result.final_capital:,.0f}")
        report.append("")
        report.append("-" * 60)
        report.append("RETURNS")
        report.append("-" * 60)
        report.append(f"Total Return: ₹{self.result.total_return:,.0f} ({self.result.total_return_pct:+.2f}%)")
        report.append("")
        report.append("-" * 60)
        report.append("TRADE STATISTICS")
        report.append("-" * 60)
        report.append(f"Total Trades: {self.result.total_trades}")
        report.append(f"Winning Trades: {self.result.winning_trades}")
        report.append(f"Losing Trades: {self.result.losing_trades}")
        report.append(f"Win Rate: {self.result.win_rate:.1f}%")
        report.append("")
        report.append("-" * 60)
        report.append("RISK METRICS")
        report.append("-" * 60)
        report.append(f"Profit Factor: {self.result.profit_factor:.2f}")
        report.append(f"Sharpe Ratio: {self.result.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio: {self.result.sortino_ratio:.2f}")
        report.append(f"Max Drawdown: ₹{self.result.max_drawdown:,.0f} ({self.result.max_drawdown_pct:.1f}%)")
        report.append("")
        report.append("-" * 60)
        report.append("TRADE DETAILS")
        report.append("-" * 60)
        report.append(f"Average Win: ₹{self.result.avg_win:,.0f}")
        report.append(f"Average Loss: ₹{self.result.avg_loss:,.0f}")
        report.append(f"Largest Win: ₹{self.result.largest_win:,.0f}")
        report.append(f"Largest Loss: ₹{self.result.largest_loss:,.0f}")
        report.append(f"Avg Hold Time: {self.result.avg_hold_time:.0f} mins")
        report.append("")

        # Individual trades
        if self.result.trades:
            report.append("-" * 60)
            report.append("TRADE LOG")
            report.append("-" * 60)
            report.append(f"{'#':>3} {'Date':>12} {'Symbol':>20} {'P&L':>10} {'Reason'}")
            report.append("-" * 60)
            for i, trade in enumerate(self.result.trades[:50], 1):  # First 50
                date_str = trade.date.strftime("%Y-%m-%d") if hasattr(trade.date, 'strftime') else str(trade.date)[:10]
                report.append(f"{i:>3} {date_str:>12} {trade.symbol:>20} {trade.pnl:>+10.0f} {trade.exit_reason}")

        report.append("")
        report.append("=" * 60)

        text = "\n".join(report)

        # Save
        if filename is None:
            filename = f"backtest_{self.result.start_date}_{self.result.end_date}.txt"

        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(text)

        logger.info(f"Text report saved to {filepath}")
        return str(filepath)

    def _calculate_monthly_returns(self) -> dict:
        """Calculate monthly returns from equity curve"""
        if len(self.result.equity_curve) < 2:
            return {'month': [], 'return': []}

        df = pd.DataFrame(self.result.equity_curve, columns=['date', 'equity'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        # Resample to monthly
        monthly = df['equity'].resample('M').last()
        returns = monthly.pct_change() * 100

        return {
            'month': [d.strftime('%Y-%m') for d in returns.index],
            'return': returns.fillna(0).tolist()
        }

    def _calculate_drawdown_series(self) -> list:
        """Calculate drawdown series"""
        if not self.result.equity_curve:
            return []

        values = [e[1] for e in self.result.equity_curve]
        peak = values[0]
        drawdown = []

        for v in values:
            if v > peak:
                peak = v
            dd = ((peak - v) / peak) * 100 if peak > 0 else 0
            drawdown.append(-dd)  # Negative for visualization

        return drawdown

    def _calculate_strategy_stats(self) -> dict:
        """Calculate wins/losses by strategy"""
        stats = {}
        for trade in self.result.trades:
            strategy = trade.strategy or 'unknown'
            if strategy not in stats:
                stats[strategy] = {'wins': 0, 'losses': 0}

            if trade.pnl > 0:
                stats[strategy]['wins'] += 1
            else:
                stats[strategy]['losses'] += 1

        return stats

    def _calculate_cumulative_pnl(self) -> list:
        """Calculate cumulative P&L"""
        if not self.result.trades:
            return []

        cum = 0
        result = []
        for trade in self.result.trades:
            cum += trade.pnl
            result.append(cum)
        return result

    def _get_metrics_text(self) -> str:
        """Get formatted metrics text for annotation"""
        return f"""
<b>METRICS</b>
─────────────
Return: {self.result.total_return_pct:+.1f}%
Win Rate: {self.result.win_rate:.0f}%
Profit Factor: {self.result.profit_factor:.2f}
Sharpe: {self.result.sharpe_ratio:.2f}
Max DD: {self.result.max_drawdown_pct:.1f}%
Trades: {self.result.total_trades}
"""

    def save_trades_csv(self, filename: str = None) -> str:
        """Save trade log to CSV"""
        if not self.result.trades:
            return None

        records = []
        for trade in self.result.trades:
            records.append({
                'trade_id': trade.trade_id,
                'date': trade.date,
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'side': trade.side,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'entry_reason': trade.entry_reason,
                'exit_reason': trade.exit_reason,
                'hold_time': trade.hold_time
            })

        df = pd.DataFrame(records)

        if filename is None:
            filename = f"trades_{self.result.start_date}_{self.result.end_date}.csv"

        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Trades saved to {filepath}")

        return str(filepath)
