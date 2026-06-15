"""HTTP response helpers for agent handlers."""

from datetime import datetime
from typing import Any


def _base(session_id: str | None) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
    }


def success_response(session_id: str | None, **fields: Any) -> dict[str, Any]:
    return {"status": "success", **_base(session_id), **fields}


def error_response(error: str, session_id: str | None) -> dict[str, Any]:
    return {"status": "error", "error": error, **_base(session_id)}
