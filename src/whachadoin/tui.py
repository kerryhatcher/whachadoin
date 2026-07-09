"""Textual TUI for whachadoin: todos + log feed, single screen."""
from __future__ import annotations

from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView

from . import db as dbmod


class WhachadoinApp(App):
    CSS = """
    #panes { height: 1fr; }
    #todos, #logs { width: 1fr; border: round $primary; }
    #entry { dock: bottom; }
    """

    BINDINGS = [
        Binding("a", "add_todo", "Add todo"),
        Binding("l", "add_log", "Add log"),
        Binding("d", "done", "Mark done"),
        Binding("r", "refresh_panes", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, db_override: Optional[str] = None) -> None:
        super().__init__()
        self.conn = dbmod.connect(db_override)
        self.todo_ids: List[int] = []
        self.input_mode: Optional[str] = None  # "todo" | "log"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panes"):
            yield ListView(id="todos")
            yield ListView(id="logs")
        yield Input(placeholder="press a to add todo, l to add log", id="entry")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh_panes()

    def action_refresh_panes(self) -> None:
        todos = self.query_one("#todos", ListView)
        todos.clear()
        self.todo_ids = []
        for t in dbmod.list_todos(self.conn):
            self.todo_ids.append(t.id)
            todos.append(ListItem(Label(f"#{t.id} (p{t.priority}) {t.text}")))
        logs = self.query_one("#logs", ListView)
        logs.clear()
        for e in dbmod.list_log(self.conn):
            logs.append(ListItem(Label(f"{e.ts[:16]}  {e.text}")))

    def _prompt(self, mode: str, placeholder: str) -> None:
        self.input_mode = mode
        entry = self.query_one("#entry", Input)
        entry.placeholder = placeholder
        entry.value = ""
        entry.focus()

    def action_add_todo(self) -> None:
        self._prompt("todo", "new todo text, then Enter")

    def action_add_log(self) -> None:
        self._prompt("log", "new log entry, then Enter")

    def action_done(self) -> None:
        todos = self.query_one("#todos", ListView)
        idx = todos.index
        if idx is None or idx >= len(self.todo_ids):
            return
        dbmod.done_todo(self.conn, self.todo_ids[idx])
        self.action_refresh_panes()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        mode, self.input_mode = self.input_mode, None
        event.input.value = ""
        if not text or mode is None:
            return
        if mode == "todo":
            dbmod.add_todo(self.conn, text)
        elif mode == "log":
            dbmod.add_log(self.conn, text)
        self.action_refresh_panes()


def run(db_override: Optional[str] = None) -> None:
    WhachadoinApp(db_override).run()
