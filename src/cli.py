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


def handle_extract(args: argparse.Namespace) -> None:
    """Run structured extraction (receipts, subscriptions, meetings, deadlines) on stored emails."""
    from src.extraction.pipeline import run_extraction_pipeline

    limit = args.limit
    console.print(
        Panel.fit(
            f"[bold cyan]IndexLens — Structured Entity Extraction (Phase 2)[/bold cyan]\n"
            f"Limit: [green]{limit}[/green] | Target: [yellow]Unextracted Receipts, Subscriptions, Meetings, Deadlines[/yellow]",
            border_style="cyan",
        )
    )

    with console.status("[bold green]Extracting structured entities via LLM / Heuristics..."):
        results = run_extraction_pipeline(limit=limit)

    table = Table(title="Extraction Results", show_lines=True)
    table.add_column("Entity Type", style="bold cyan")
    table.add_column("Count Extracted", justify="right", style="green")

    table.add_row("Processed Unextracted Emails", str(results["processed_count"]))
    table.add_row("Financial Receipts", str(results["receipts_extracted"]))
    table.add_row("Active Subscriptions Detected", str(results["subscriptions_detected"]))
    table.add_row("Meetings / Calendar Invites", str(results["meetings_extracted"]))
    table.add_row("Urgent Deadlines / Action Items", str(results["deadlines_extracted"]))
    table.add_row("Resolved Ambiguous (NEEDS_LLM)", str(results.get("resolved_llm_count", 0)))

    console.print(table)
    console.print(
        f"[bold green][OK] Extraction completed successfully.[/bold green]"
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

    # extract
    extract_parser = subparsers.add_parser("extract", help="Extract structured entities (receipts, subscriptions, meetings, deadlines)")
    extract_parser.add_argument("--limit", type=int, default=100, help="Number of emails to extract (default: 100)")
    extract_parser.set_defaults(func=handle_extract)

    # test-llm
    test_llm_parser = subparsers.add_parser("test-llm", help="Test live connection to OpenRouter LLM")
    test_llm_parser.set_defaults(func=handle_test_llm)

    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI REST backend server for Lovable UI")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    serve_parser.set_defaults(func=handle_serve)

    # launch
    launch_parser = subparsers.add_parser("launch", help="Launch full-stack product (FastAPI + Vite Dashboard + Forwarder)")
    launch_parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    launch_parser.add_argument("--ui-port", type=int, default=8080, help="UI port (default: 8080)")
    launch_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open default browser")
    launch_parser.set_defaults(func=handle_launch)

    args = parser.parse_args()
    args.func(args)



def handle_test_llm(args: argparse.Namespace) -> None:
    """Test connectivity to OpenRouter using configured model."""
    import datetime as dt
    from src.config import OPENROUTER_API_KEY, EXTRACTION_MODEL, OPENROUTER_BASE_URL
    from src.extraction.extractor import LLMExtractor
    from src.schemas.email_schemas import RawEmail

    console.print(
        Panel.fit(
            f"[bold cyan]IndexLens — OpenRouter LLM Connectivity Test[/bold cyan]\n"
            f"Base URL: [green]{OPENROUTER_BASE_URL}[/green]\n"
            f"Model: [green]{EXTRACTION_MODEL}[/green]",
            border_style="cyan",
        )
    )

    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        console.print(
            "[bold red][X] No API Key detected in .env![/bold red]\n"
            "Please paste your OpenRouter key into .env: [yellow]OPENROUTER_API_KEY=sk-or-v1-...[/yellow] and save the file (Ctrl+S)."
        )
        return

    console.print(f"[dim]Key detected: {OPENROUTER_API_KEY[:8]}... (length: {len(OPENROUTER_API_KEY)})[/dim]")
    extractor = LLMExtractor()
    if not extractor.is_live:
        console.print("[bold red]Extractor failed to initialize live client with provided key.[/bold red]")
        return

    sample = RawEmail(
        id="test_msg_001",
        thread_id="test_th_001",
        sender="Swiggy <orders@swiggy.in>",
        sender_email="orders@swiggy.in",
        sender_domain="swiggy.in",
        subject="Your order from Burger King has been delivered",
        date=dt.datetime.now(dt.timezone.utc),
        snippet="Total paid: ₹485.50 via UPI.",
        body_plain="Order Details: Whopper Meal x 1. Item total: ₹450. Taxes: ₹35.50. Total amount: ₹485.50. Payment mode: Google Pay UPI.",
        labels=["INBOX", "RECEIPTS"],
    )

    with console.status(f"[bold green]Sending test extraction request to {EXTRACTION_MODEL}..."):
        try:
            extracted = extractor._extract_llm(sample, hint="RECEIPT")
            console.print(f"[bold green][OK] Connection successful! Model extracted structured output:[/bold green]")
            console.print(extracted.model_dump_json(indent=2))
        except Exception as err:
            console.print(f"[bold red][X] OpenRouter call failed:[/bold red] {err}")


def handle_serve(args: argparse.Namespace) -> None:
    """Launch the FastAPI server."""
    import uvicorn
    console.print(
        Panel.fit(
            f"[bold cyan]IndexLens — API Server Running[/bold cyan]\n"
            f"Host: [green]{args.host}[/green] | Port: [green]{args.port}[/green]\n"
            f"API Docs: [bold blue]http://{args.host}:{args.port}/docs[/bold blue]",
            border_style="cyan",
        )
    )
    uvicorn.run("src.api.main:app", host=args.host, port=args.port, reload=args.reload)


def handle_launch(args: argparse.Namespace) -> None:
    """Launch full stack: FastAPI backend, Vite dev server, forwarder proxy, and auto-open browser."""
    import subprocess
    import time
    import webbrowser
    from src.config import BASE_DIR

    console.print(
        Panel.fit(
            "[bold cyan]IndexLens — Launching Full-Stack Application[/bold cyan]\n"
            f"Backend API: [green]http://127.0.0.1:{args.backend_port}[/green]\n"
            f"Dashboard UI: [green]http://localhost:{args.ui_port}[/green]\n"
            f"Forwarder: [green]http://localhost:5173[/green]\n"
            "Press [bold red]Ctrl+C[/bold red] to stop all services.",
            border_style="cyan",
        )
    )

    processes = []
    try:
        # 1. Start Backend API
        backend_cmd = [sys.executable, "-m", "src.cli", "serve", "--port", str(args.backend_port)]
        backend_proc = subprocess.Popen(backend_cmd, cwd=str(BASE_DIR))
        processes.append(("Backend", backend_proc))

        # 2. Start Frontend Vite
        frontend_dir = BASE_DIR / "frontend"
        if frontend_dir.exists():
            frontend_cmd = ["npm.cmd" if sys.platform == "win32" else "npm", "run", "dev"]
            frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(frontend_dir))
            processes.append(("Frontend", frontend_proc))

        # 3. Start Port 5173 Forwarder if proxy5173.js exists
        proxy_script = BASE_DIR / "proxy5173.js"
        if proxy_script.exists():
            proxy_cmd = ["node", str(proxy_script)]
            proxy_proc = subprocess.Popen(proxy_cmd, cwd=str(BASE_DIR))
            processes.append(("Proxy5173", proxy_proc))

        time.sleep(3)

        if not args.no_browser:
            webbrowser.open(f"http://localhost:{args.ui_port}")

        console.print("[bold green]All services running! Listening for requests...[/bold green]")

        # Keep running until interrupted
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    console.print(f"[yellow]Process {name} exited with code {proc.returncode}[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopping IndexLens services...[/bold yellow]")
    finally:
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        console.print("[bold green]All services stopped cleanly.[/bold green]")


if __name__ == "__main__":
    main()

