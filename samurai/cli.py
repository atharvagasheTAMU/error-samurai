from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.capture import capture_incident, load_last_error
from core.search import SearchOutcome, search_memories_for_query
from core.solved import SolvedResult, solve_active_incident

app = typer.Typer(
    help="Local-first debugging memory for recurring errors.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def capture(
    error: Optional[str] = typer.Argument(None, help="Error text to capture."),
    last: bool = typer.Option(False, "--last", help="Capture the last known error."),
) -> None:
    """Capture a debugging incident."""
    if last:
        error = load_last_error()
        if not error:
            console.print("[red]No last error found in Error Samurai logs.[/red]")
            raise typer.Exit(code=1)

    if not error:
        error = Prompt.ask("Paste the error to capture").strip()

    try:
        result = capture_incident(error)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    incident = result.incident
    replaced = " Replaced the previous active incident for this repo." if result.replaced_incident else ""
    console.print(
        Panel(
            f"[bold green]Captured incident #{incident['id']}[/bold green]\n"
            f"Fingerprint: [cyan]{incident['fingerprint']}[/cyan]\n"
            f"Language: {incident['language'] or 'unknown'}\n"
            f"Repo: {incident['repo_path']}\n"
            f"{replaced}",
            title="Error Samurai",
        )
    )


@app.command()
def search(query: Optional[str] = typer.Argument(None, help="Search text.")) -> None:
    """Search prior debugging memories."""
    try:
        outcome = search_memories_for_query(query)
    except LookupError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=1) from exc

    _render_search(outcome)


@app.command()
def solved(
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Short note about the fix."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Save without prompting."),
    skip: bool = typer.Option(False, "--skip", help="Close the incident without saving memory."),
    force_permanent: bool = typer.Option(
        False,
        "--force-permanent",
        help="Save even if the fix looks trivial.",
    ),
) -> None:
    """Convert an active incident into reusable memory."""
    save_memory = not skip
    if save_memory and not yes:
        save_memory = typer.confirm("Save memory?", default=True)
    if save_memory and note is None:
        note = Prompt.ask("Optional note", default="")

    try:
        result = solve_active_incident(
            note=note,
            save_memory=save_memory,
            force_permanent=force_permanent,
        )
    except LookupError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=1) from exc

    _render_solved(result)


def _render_search(outcome: SearchOutcome) -> None:
    if not outcome.results:
        console.print(f"[yellow]No memories found for {outcome.source}: {outcome.query}[/yellow]")
        return

    console.print(f"[bold]Top matches for {outcome.source}:[/bold] {outcome.query}")
    for index, memory in enumerate(outcome.results, start=1):
        tags = ", ".join(memory.get("tags") or []) or "none"
        diff_preview = memory.get("diff_path") or "no diff artifact"
        body = (
            f"[bold]{memory['title']}[/bold]\n"
            f"Confidence: {float(memory['confidence']):.2f} | Match score: {float(memory['score']):.2f}\n"
            f"Root cause: {memory['root_cause']}\n"
            f"Fix steps:\n{memory['fix_steps']}\n"
            f"Diff: {diff_preview}\n"
            f"Tags: {tags}\n"
            f"Saved: {memory['created_at']}"
        )
        console.print(Panel(body, title=f"Match {index}"))


def _render_solved(result: SolvedResult) -> None:
    table = Table(title="Solved Incident")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Incident", f"#{result.incident['id']}")
    table.add_row("Changed files", str(len(result.diff_metadata.changed_files)))
    table.add_row("Lines", f"+{result.diff_metadata.additions} / -{result.diff_metadata.removals}")
    table.add_row("Tests modified", "yes" if result.diff_metadata.tests_modified else "no")
    table.add_row("Config modified", "yes" if result.diff_metadata.config_files_modified else "no")
    console.print(table)

    if result.skipped:
        console.print("[yellow]Closed active incident without saving memory.[/yellow]")
    elif result.memory:
        console.print(f"[green]Saved memory #{result.memory['id']}[/green]")
    if result.trivial_reasons:
        console.print("[dim]Triviality signals: " + ", ".join(result.trivial_reasons) + "[/dim]")
