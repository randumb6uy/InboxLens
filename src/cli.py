"""IndexLens CLI entrypoint."""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.ingestion.client import GmailClient
from src.pipeline import run_ingestion_pipeline
from src.storage.db import Database

# Ensure UTF-8 stdout on Windows where possible
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

console = Console(safe_box=True)


def handle_fetch(args: argparse.Namespace) -> None:
    """Fetch emails and display summary table and details."""
    limit = args.limit
    query = args.query
    mock = True if args.mock else (False if args.live else None)

    console.print(
        Panel.fit(
            f"[bold cyan]IndexLens — Email Ingestion[/bold cyan]\n"
            f"Limit: [green]{limit}[/green] | Query: [yellow]{query or 'None'}[/yellow] | Mode: [magenta]{'Mock' if mock else 'Auto/Live'}[/magenta]",
            border_style="cyan",
        )
    )

    with console.status("[bold green]Connecting & fetching emails..."):
        client = GmailClient(mock=mock)
        emails = client.fetch_recent_emails(limit=limit, query=query)

    if not emails:
        console.print("[yellow]No emails found matching criteria.[/yellow]")
        return

    table = Table(title=f"Ingested Emails ({len(emails)} items)", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", style="cyan", width=16)
    table.add_column("Sender", style="green", width=28)
    table.add_column("Subject", style="bold white", width=36)
    table.add_column("Snippet / Body Preview", style="white")

    for idx, email_item in enumerate(emails, 1):
        date_str = email_item.date.strftime("%Y-%m-%d %H:%M")
        snippet = email_item.snippet.replace("\n", " ").strip()
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        table.add_row(
            str(idx),
            date_str,
            email_item.sender[:26],
            email_item.subject[:34],
            snippet,
        )

    console.print(table)
    console.print(
        f"[bold green][OK] Successfully fetched and parsed {len(emails)} emails.[/bold green]"
    )


def handle_ingest(args: argparse.Namespace) -> None:
    """Ingest emails, route deterministically, and store in SQLite."""
    limit = args.limit
    query = args.query
    mock = True if args.mock else (False if args.live else None)

    console.print(
        Panel.fit(
            f"[bold cyan]IndexLens — Pipeline Batch Ingestion & Classification[/bold cyan]\n"
            f"Limit: [green]{limit}[/green] | Query: [yellow]{query or 'None'}[/yellow] | Mode: [magenta]{'Mock' if mock else 'Auto/Live'}[/magenta]",
            border_style="cyan",
        )
    )

    with console.status("[bold green]Running ingestion and deterministic classification..."):
        emails, stats = run_ingestion_pipeline(limit=limit, query=query, mock=mock)

    table = Table(title="Inbox Classification Breakdown (Phase 1)", show_lines=True)
    table.add_column("Category", style="bold cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Share", justify="right", style="magenta")
    table.add_column("LLM Needed?", justify="center", style="yellow")

    total = stats.get("total", len(emails))
    for cat, count in stats.get("breakdown", {}).items():
        share = f"{(count / total * 100):.1f}%" if total > 0 else "0%"
        needs_llm_str = "[red]Yes (Ambiguous)[/red]" if cat == "NEEDS_LLM" else "[green]No (Zero Cost)[/green]"
        table.add_row(cat, str(count), share, needs_llm_str)

    console.print(table)

    det_rate = stats.get("deterministic_rate", 0.0)
    color = "green" if det_rate >= 60.0 else "yellow"
    console.print(
        Panel.fit(
            f"Total Processed: [bold]{total}[/bold]\n"
            f"Zero-Cost Classified: [bold {color}]{stats.get('deterministic_count', 0)} ({det_rate}%)[/bold {color}]\n"
            f"Escalated to LLM: [bold yellow]{stats.get('needs_llm_count', 0)}[/bold yellow]\n"
            f"Exit Criteria (60–70%): [{'green]MET' if det_rate >= 60.0 else 'red]BELOW TARGET'}[/]",
            title="Deterministic Efficiency",
            border_style=color,
        )
    )


def handle_stats(args: argparse.Namespace) -> None:
    """Show current database classification statistics."""
    db = Database()
    stats = db.get_classification_stats()
    total = stats.get("total", 0)

    if total == 0:
        console.print("[yellow]Database is empty. Run 'indexlens ingest' first.[/yellow]")
        return

    table = Table(title=f"Stored Emails Statistics ({total} total)", show_lines=True)
    table.add_column("Category", style="bold cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Share", justify="right", style="magenta")

    for cat, count in stats.get("breakdown", {}).items():
        share = f"{(count / total * 100):.1f}%"
        table.add_row(cat, str(count), share)

    console.print(table)
    console.print(
        f"[bold green]Deterministic rate: {stats.get('deterministic_rate')}% zero-cost classified.[/bold green]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="IndexLens — AI-Powered Gmail Data & Stats Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch recent emails from Gmail or mock provider")
    fetch_parser.add_argument("--limit", type=int, default=100, help="Number of emails to fetch (default: 100)")
    fetch_parser.add_argument("--query", type=str, default=None, help="Gmail search query filter")
    fetch_parser.add_argument("--mock", action="store_true", help="Force synthetic mock data")
    fetch_parser.add_argument("--live", action="store_true", help="Force live Gmail API connection")
    fetch_parser.set_defaults(func=handle_fetch)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Run batch ingestion and deterministic classification into SQLite")
    ingest_parser.add_argument("--limit", type=int, default=100, help="Number of emails to ingest (default: 100)")
    ingest_parser.add_argument("--query", type=str, default=None, help="Gmail search query filter")
    ingest_parser.add_argument("--mock", action="store_true", help="Force synthetic mock data")
    ingest_parser.add_argument("--live", action="store_true", help="Force live Gmail API connection")
    ingest_parser.set_defaults(func=handle_ingest)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Display inbox classification statistics from SQLite")
    stats_parser.set_defaults(func=handle_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
