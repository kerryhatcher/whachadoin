"""Pydantic models mirroring the todos and log tables."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class Todo(BaseModel):
    id: Optional[int] = None
    text: str
    status: Literal["open", "done"] = "open"
    priority: int = 0
    created_at: str
    done_at: Optional[str] = None


class LogEntry(BaseModel):
    id: Optional[int] = None
    ts: str
    text: str
    todo_id: Optional[int] = None
    path: str = ""
    repo: Optional[str] = None
