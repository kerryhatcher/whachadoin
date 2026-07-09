"""Typer CLI for whachadoin. Console command: kwd."""
from __future__ import annotations

from typing import List, NoReturn, Optional

import typer

from . import db as dbmod

app = typer.Typer(help="whachadoin — work log + todo tracker", no_args_is_help=True)
todo_app = typer.Typer(help="manage todos", no_args_is_help=True)
app.add_typer(todo_app, name="todo")


@app.callback()
def _main(
    ctx: typer.Context,
    db: Optional[str] = typer.Option(None, "--db", help="override the DB path"),
) -> None:
    """Store the optional DB override for subcommands to read."""
    ctx.obj = db


def _fail(message: str) -> NoReturn:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(1)


@app.command()
def log(
    ctx: typer.Context,
    words: Optional[List[str]] = typer.Argument(
        None, help='log text, or "ls" to list entries'
    ),
    today: bool = typer.Option(False, "--today", help="ls: only today's entries"),
    since: Optional[str] = typer.Option(
        None, "--since", help="ls: entries since YYYY-MM-DD"
    ),
) -> None:
    """Add a log entry, or `kwd log ls` to list entries newest-first."""
    conn = dbmod.connect(ctx.obj)
    words = list(words or [])
    if words and words[0] == "ls":
        for e in dbmod.list_log(conn, today=today, since=since):
            link = f" (todo #{e.todo_id})" if e.todo_id else ""
            tag = f"[{e.repo}] " if e.repo else ""
            typer.echo(f"{e.ts}  {tag}{e.text}{link}")
        return
    text = " ".join(words).strip()
    try:
        entry = dbmod.add_log(conn, text)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"logged #{entry.id}")


@todo_app.command("add")
def todo_add(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="todo text"),
    priority: int = typer.Option(0, "--priority", help="higher = more urgent"),
) -> None:
    """Add an open todo."""
    conn = dbmod.connect(ctx.obj)
    try:
        todo = dbmod.add_todo(conn, text, priority=priority)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"added todo #{todo.id}")


@todo_app.command("done")
def todo_done(
    ctx: typer.Context,
    todo_id: int = typer.Argument(..., help="id of the todo to complete"),
) -> None:
    """Mark a todo done and record a linked log entry."""
    conn = dbmod.connect(ctx.obj)
    try:
        todo = dbmod.done_todo(conn, todo_id)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"done: #{todo.id} {todo.text}")


@todo_app.command("ls")
def todo_ls(
    ctx: typer.Context,
    all_: bool = typer.Option(False, "--all", help="include done todos"),
) -> None:
    """List open todos (--all includes done), priority desc then created."""
    conn = dbmod.connect(ctx.obj)
    for t in dbmod.list_todos(conn, include_done=all_):
        typer.echo(f"#{t.id}  p{t.priority}  {t.status:<4}  {t.text}")


@app.command()
def tui(ctx: typer.Context) -> None:
    """Launch the Textual TUI."""
    from .tui import run

    run(ctx.obj)
