import pytest
from pydantic import ValidationError

from whachadoin.models import Todo, LogEntry


def test_todo_defaults_and_valid_status():
    t = Todo(text="write plan", created_at="2026-07-09T00:00:00+00:00")
    assert t.id is None
    assert t.status == "open"
    assert t.priority == 0
    assert t.done_at is None


def test_todo_rejects_bad_status():
    with pytest.raises(ValidationError):
        Todo(text="x", status="finished", created_at="2026-07-09T00:00:00+00:00")


def test_logentry_defaults():
    e = LogEntry(ts="2026-07-09T00:00:00+00:00", text="did a thing")
    assert e.id is None
    assert e.todo_id is None


from pathlib import Path

from whachadoin import db as dbmod


def test_default_path_uses_xdg_when_set(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")
    assert dbmod.default_db_path() == Path("/tmp/xdg/whachadoin/log.db")


def test_default_path_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/tester")))
    assert dbmod.default_db_path() == Path("/home/tester/.whachadoin/log.db")


def test_resolve_precedence(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")
    monkeypatch.setenv("WHACHADOIN_DB", "/tmp/env.db")
    # explicit override wins over env and default
    assert dbmod.resolve_db_path("/tmp/explicit.db") == Path("/tmp/explicit.db")
    # env wins over default
    assert dbmod.resolve_db_path(None) == Path("/tmp/env.db")
    # default used when neither given
    monkeypatch.delenv("WHACHADOIN_DB", raising=False)
    assert dbmod.resolve_db_path(None) == Path("/tmp/xdg/whachadoin/log.db")


@pytest.fixture
def conn(tmp_path):
    c = dbmod.connect(tmp_path / "log.db")
    yield c
    c.close()


def test_connect_creates_parent_dir(tmp_path):
    target = tmp_path / "nested" / "dir" / "log.db"
    c = dbmod.connect(target)
    c.close()
    assert target.exists()


def test_add_and_list_todo(conn):
    t = dbmod.add_todo(conn, "buy milk", priority=2)
    assert t.id is not None
    assert t.status == "open"
    todos = dbmod.list_todos(conn)
    assert [x.text for x in todos] == ["buy milk"]


def test_list_todos_sorted_by_priority_then_created(conn):
    dbmod.add_todo(conn, "low", priority=0)
    dbmod.add_todo(conn, "high", priority=5)
    dbmod.add_todo(conn, "mid", priority=1)
    assert [t.text for t in dbmod.list_todos(conn)] == ["high", "mid", "low"]


def test_add_todo_rejects_empty_text(conn):
    with pytest.raises(ValueError):
        dbmod.add_todo(conn, "   ")


def test_done_todo_links_log_entry(conn):
    t = dbmod.add_todo(conn, "ship it")
    updated = dbmod.done_todo(conn, t.id)
    assert updated.status == "done"
    assert updated.done_at is not None
    entries = dbmod.list_log(conn)
    assert len(entries) == 1
    assert entries[0].todo_id == t.id


def test_done_missing_todo_raises(conn):
    with pytest.raises(ValueError):
        dbmod.done_todo(conn, 999)


def test_list_todos_excludes_done_by_default(conn):
    t = dbmod.add_todo(conn, "done soon")
    dbmod.done_todo(conn, t.id)
    assert dbmod.list_todos(conn) == []
    assert len(dbmod.list_todos(conn, include_done=True)) == 1


def test_add_log_freestanding(conn):
    e = dbmod.add_log(conn, "read the spec")
    assert e.id is not None
    assert e.todo_id is None
    assert dbmod.list_log(conn)[0].text == "read the spec"


def test_add_log_rejects_empty_text(conn):
    with pytest.raises(ValueError):
        dbmod.add_log(conn, "")


def test_list_log_since_filter(conn):
    dbmod.add_log(conn, "old")  # today's entry
    # a since date in the future excludes everything
    assert dbmod.list_log(conn, since="2999-01-01") == []
    # a since date in the past includes it
    assert len(dbmod.list_log(conn, since="2000-01-01")) == 1
