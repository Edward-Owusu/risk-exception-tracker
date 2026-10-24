"""Convert a register to and from plain rows, for the dashboard's editable table."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

from .engine import REGISTER_COLUMNS, Exception_, parse_register

DATE_COLUMNS = {"approved_date", "expiry_date", "control_verified_date", "remediation_due", "closed_date"}


def register_rows(exceptions: list[Exception_]) -> list[dict[str, Any]]:
    """One dict per exception, with real date objects so a table editor can show date pickers."""
    return [{col: getattr(e, col) for col in REGISTER_COLUMNS} for e in exceptions]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN and pandas NaT are not equal to themselves
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text in ("NaT", "nan", "None"):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return text


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(REGISTER_COLUMNS)
    for row in rows:
        w.writerow([_cell(row.get(col)) for col in REGISTER_COLUMNS])
    return buf.getvalue()


def rows_to_register(rows: list[dict[str, Any]], model: dict | None = None) -> list[Exception_]:
    """Validate edited rows by passing them through the same parser as an uploaded file."""
    return parse_register(rows_to_csv(rows), model)
