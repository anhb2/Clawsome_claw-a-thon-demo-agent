"""Read/write dashboard data and run CSV parsers."""

from __future__ import annotations

import json
from pathlib import Path

from app.data.paths import (
    EVENT_DASHBOARD_JSON,
    EVENT_RAW_CSV,
    PAYMENT_DASHBOARD_JSON,
    PAYMENT_RAW_CSV,
    ensure_data_dirs,
)
from app.parsers import parse_event_csv, parse_payment_csv


def save_payment_csv(content: bytes) -> Path:
    ensure_data_dirs()
    PAYMENT_RAW_CSV.write_bytes(content)
    return PAYMENT_RAW_CSV


def save_event_csv(content: bytes) -> Path:
    ensure_data_dirs()
    EVENT_RAW_CSV.write_bytes(content)
    return EVENT_RAW_CSV


def process_payment_csv() -> dict:
    ensure_data_dirs()
    if not PAYMENT_RAW_CSV.exists():
        raise FileNotFoundError(f"Missing payment CSV: {PAYMENT_RAW_CSV}")
    return parse_payment_csv(PAYMENT_RAW_CSV, PAYMENT_DASHBOARD_JSON)


def process_event_csv() -> dict:
    ensure_data_dirs()
    if not EVENT_RAW_CSV.exists():
        raise FileNotFoundError(f"Missing event CSV: {EVENT_RAW_CSV}")
    return parse_event_csv(EVENT_RAW_CSV, EVENT_DASHBOARD_JSON)


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_dashboard_payload() -> dict:
    """Return processed dashboard JSON for the frontend."""
    ensure_data_dirs()
    return {
        "payment": _read_json(PAYMENT_DASHBOARD_JSON),
        "events": _read_json(EVENT_DASHBOARD_JSON),
    }


def seed_from_project_root() -> None:
    """Build processed JSON from bundled CSVs in data/raw/ when needed."""
    ensure_data_dirs()
    if PAYMENT_RAW_CSV.exists() and not PAYMENT_DASHBOARD_JSON.exists():
        process_payment_csv()
    if EVENT_RAW_CSV.exists() and not EVENT_DASHBOARD_JSON.exists():
        process_event_csv()
