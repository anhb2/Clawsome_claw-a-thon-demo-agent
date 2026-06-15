"""Single source of truth for raw CSV and processed JSON locations."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

PAYMENT_RAW_CSV = RAW_DIR / "payment_raw.csv"
EVENT_RAW_CSV = RAW_DIR / "event_raw.csv"
PAYMENT_DASHBOARD_JSON = PROCESSED_DIR / "payment_dashboard.json"
EVENT_DASHBOARD_JSON = PROCESSED_DIR / "event_dashboard.json"

DASHBOARD_HTML = PROJECT_ROOT / "app" / "web" / "static" / "dashboard.html"


def ensure_data_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
