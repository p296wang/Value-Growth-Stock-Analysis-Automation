"""Command line entry point: `analyze TICKER`."""

from __future__ import annotations

import logging
import sys
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from stock_analyzer import criteria
from stock_analyzer.analysis import build_report
from stock_analyzer.data.provider import FixtureProvider, TickerNotFound, save_fixture
from stock_analyzer.data.sec_edgar import SecEdgarClient, SecEdgarError
from stock_analyzer.report import markdown, terminal


class ExportFormat(str, Enum):
    md = "md"


def analyze(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol, e.g. ALAB")],
    export: Annotated[Optional[ExportFormat], typer.Option(help="Also write the report to a file.")] = None,
    output_dir: Annotated[Path, typer.Option(help="Folder for exported reports.")] = Path("reports"),
    eps_10y_ago: Annotated[Optional[float], typer.Option(help="Override: EPS from 10 years ago.")] = None,
    min_pe: Annotated[Optional[float], typer.Option(help="Override: lowest P/E in the last 10 years.")] = None,
    offline: Annotated[Optional[Path], typer.Option(help="Analyze a saved JSON fixture instead of live data.")] = None,
    save_fixture_to: Annotated[Optional[Path], typer.Option("--save-fixture", help="Save fetched data as JSON.")] = None,
    config: Annotated[Optional[Path], typer.Option(help="Custom thresholds YAML file.")] = None,
) -> None:
    """Classify a stock as a value or growth stock and explain why."""
    console = Console()
    logging.basicConfig(level=logging.ERROR)

    if offline is not None:
        provider = FixtureProvider(offline)
    else:
        from stock_analyzer.data.yfinance_provider import YFinanceProvider  # slow import, only when needed

        try:
            sec = SecEdgarClient.from_env()
        except SecEdgarError as exc:
            console.print(f"[yellow]Skipping SEC EDGAR: {exc}[/yellow]")
            sec = None
        provider = YFinanceProvider(sec=sec)

    try:
        with console.status(f"Fetching data for {ticker.upper()}..."):
            data = provider.fetch(ticker)
    except TickerNotFound as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if save_fixture_to is not None:
        save_fixture(data, save_fixture_to)
        console.print(f"[dim]Saved data to {save_fixture_to}[/dim]")

    report = build_report(data, criteria.load_config(config), eps_then_override=eps_10y_ago,
                          min_pe_override=min_pe)
    terminal.render(report, console)

    if export == ExportFormat.md:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{report.profile.ticker}_{date.today().isoformat()}.md"
        path.write_text(markdown.render(report), encoding="utf-8")
        console.print(f"\nReport saved to [bold]{path}[/bold]")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    typer.run(analyze)


if __name__ == "__main__":
    main()
