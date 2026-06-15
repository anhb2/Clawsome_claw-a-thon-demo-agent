#!/usr/bin/env python3
"""Parse ZaloPay Cinema event tracking CSV into funnel dashboard JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.data.paths import EVENT_DASHBOARD_JSON, EVENT_RAW_CSV

DEFAULT_INPUT = str(EVENT_RAW_CSV)
DEFAULT_OUTPUT = str(EVENT_DASHBOARD_JSON)

DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
PLATFORMS = ["Android", "iOS"]
NETWORKS = ["Wifi", "4G", "5G", "3G"]
SEGMENTS = ["VIP", "Regular", "Member", "New"]
EVENT_TYPES = ["view", "click", "submit"]

SCREEN_ID_MAP = {
    "1020": 1,
    "1021": 2,
    "1022": 3,
    "1023": 4,
    "1024": 5,
    "1025": 6,
    "1026": 7,
}

FUNNEL_STEPS = [
    (1, "1020", "Movie Home"),
    (2, "1021", "Phim Detail"),
    (3, "1022", "Chọn Suất Chiếu"),
    (4, "1023", "Chọn Ghế"),
    (5, "1024", "Chọn Bắp Nước"),
    (6, "1025", "Confirm"),
    (7, "1026", "Thanh Toán"),
]


def parse_num(value: str | int | float | None) -> int:
    """'36,020' | '36020' | '' | 0 → int."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text or text in ("0", ""):
        return 0
    try:
        return int(re.sub(r"[,\s]", "", text))
    except ValueError:
        return 0


def parse_dt(value: str) -> datetime | None:
    """Hỗ trợ nhiều format. Trả None nếu lỗi."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def screen_id_of(event_id: str) -> str:
    """'1020.007' → '1020'."""
    return str(event_id).split(".")[0]


def pct(value: float) -> float:
    return round(value, 1)


def empty_breakdown() -> dict[str, dict[str, int]]:
    return {
        "by_platform": {key: 0 for key in PLATFORMS},
        "by_network": {key: 0 for key in NETWORKS},
        "by_segment": {key: 0 for key in SEGMENTS},
    }


def load_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                {
                    **raw,
                    "event_sequence": parse_num(raw.get("event_sequence")),
                    "duration_ms": parse_num(raw.get("duration_ms")),
                    "tracking_dt": parse_dt(raw.get("tracking_time", "")),
                }
            )
    return rows


def build_sessions(rows: list[dict]) -> dict[str, dict]:
    sessions: dict[str, dict] = {}

    for row in rows:
        session_id = row["session_tracking_id"]
        if session_id not in sessions:
            sessions[session_id] = {
                "user_id": row.get("user_id", ""),
                "platform": row.get("platform", ""),
                "network": row.get("network", ""),
                "user_segment": row.get("user_segment", ""),
                "app_version": row.get("app_version", ""),
                "max_step": 0,
                "screens_reached": set(),
                "screen_durations": defaultdict(list),
                "tracking_times": [],
                "events": [],
            }

        session = sessions[session_id]
        session["events"].append(row)

        screen_id = screen_id_of(row["event_id"])
        duration = row["duration_ms"]
        if duration > 0:
            session["screen_durations"][screen_id].append(duration)

        if row["tracking_dt"]:
            session["tracking_times"].append(row["tracking_dt"])

        if screen_id in SCREEN_ID_MAP:
            step = SCREEN_ID_MAP[screen_id]
            session["screens_reached"].add(screen_id)
            session["max_step"] = max(session["max_step"], step)

        if not session["platform"]:
            session["platform"] = row.get("platform", "")
        if not session["network"]:
            session["network"] = row.get("network", "")
        if not session["user_segment"]:
            session["user_segment"] = row.get("user_segment", "")

    return sessions


def _sessions_reached_count(sessions: dict[str, dict], step: int) -> int:
    return sum(1 for session in sessions.values() if session["max_step"] >= step)


def _increment_breakdown(breakdown: dict[str, dict[str, int]], session: dict) -> None:
    platform = session.get("platform", "")
    network = session.get("network", "")
    segment = session.get("user_segment", "")
    if platform in breakdown["by_platform"]:
        breakdown["by_platform"][platform] += 1
    if network in breakdown["by_network"]:
        breakdown["by_network"][network] += 1
    if segment in breakdown["by_segment"]:
        breakdown["by_segment"][segment] += 1


def build_funnel_section(sessions: dict[str, dict], total_sessions: int) -> list[dict]:
    step_reached_counts = {
        step: _sessions_reached_count(sessions, step) for step, _, _ in FUNNEL_STEPS
    }
    step_durations: dict[int, list[int]] = defaultdict(list)
    step_breakdowns: dict[int, dict] = {step: empty_breakdown() for step, _, _ in FUNNEL_STEPS}

    for session in sessions.values():
        max_step = session["max_step"]
        for step, screen_id, _ in FUNNEL_STEPS:
            if max_step >= step:
                _increment_breakdown(step_breakdowns[step], session)

        for event in session["events"]:
            screen_id = screen_id_of(event["event_id"])
            if screen_id not in SCREEN_ID_MAP:
                continue
            step = SCREEN_ID_MAP[screen_id]
            if step <= max_step and event["duration_ms"] > 0:
                step_durations[step].append(event["duration_ms"])

    funnel_steps = []
    prev_reached = total_sessions
    for step, screen_id, screen_name in FUNNEL_STEPS:
        sessions_reached = step_reached_counts[step]

        if sessions_reached == 0:
            reach_pct = 0.0
            step_conversion_pct = 0.0
            dropoff_pct = 100.0 if step > 1 else 0.0
            sessions_dropped = prev_reached if step > 1 else 0
            avg_duration_ms = 0
        else:
            reach_pct = pct((sessions_reached / total_sessions) * 100) if total_sessions else 0.0
            if step == 1:
                step_conversion_pct = 100.0
                dropoff_pct = 0.0
                sessions_dropped = 0
            else:
                step_conversion_pct = pct((sessions_reached / prev_reached) * 100) if prev_reached else 0.0
                dropoff_pct = pct(100 - step_conversion_pct)
                sessions_dropped = prev_reached - sessions_reached

            durations = step_durations[step]
            avg_duration_ms = round(sum(durations) / len(durations)) if durations else 0

        funnel_steps.append(
            {
                "step": step,
                "screen_id": screen_id,
                "screen_name": screen_name,
                "sessions_reached": sessions_reached,
                "sessions_dropped": sessions_dropped,
                "reach_pct": reach_pct,
                "step_conversion_pct": step_conversion_pct,
                "dropoff_pct": dropoff_pct,
                "avg_duration_ms": avg_duration_ms,
                "breakdown": step_breakdowns[step],
            }
        )
        prev_reached = sessions_reached

    return funnel_steps


def build_meta(
    rows: list[dict],
    sessions: dict[str, dict],
    funnel_steps: list[dict],
    source_file: str,
    generated_at: str,
) -> dict:
    total_sessions = len(sessions)
    total_events = len(rows)
    sessions_reached_step_7 = _sessions_reached_count(sessions, 7)
    overall_conversion_pct = pct((sessions_reached_step_7 / total_sessions) * 100) if total_sessions else 0.0

    session_durations = []
    for session in sessions.values():
        times = session["tracking_times"]
        if len(times) >= 2:
            duration_seconds = (max(times) - min(times)).total_seconds()
            session_durations.append(duration_seconds)
    avg_session_duration_s = round(sum(session_durations) / len(session_durations)) if session_durations else 0

    biggest_dropoff_step = 2
    biggest_dropoff_pct = 0.0
    biggest_dropoff_screen = FUNNEL_STEPS[1][2]
    for step_data in funnel_steps:
        step = step_data["step"]
        if step >= 2 and step_data["dropoff_pct"] > biggest_dropoff_pct:
            biggest_dropoff_pct = step_data["dropoff_pct"]
            biggest_dropoff_step = step
            biggest_dropoff_screen = step_data["screen_name"]

    event_type_counts = {event_type: 0 for event_type in EVENT_TYPES}
    for row in rows:
        event_type = row.get("event_type", "")
        if event_type in event_type_counts:
            event_type_counts[event_type] += 1

    return {
        "generated_at": generated_at,
        "source_file": source_file,
        "total_events": total_events,
        "total_sessions": total_sessions,
        "overall_conversion_pct": overall_conversion_pct,
        "avg_session_duration_s": avg_session_duration_s,
        "biggest_dropoff_step": biggest_dropoff_step,
        "biggest_dropoff_screen": biggest_dropoff_screen,
        "biggest_dropoff_pct": biggest_dropoff_pct,
        "event_type_counts": event_type_counts,
    }


def build_sessions_by_day(sessions: dict[str, dict]) -> list[dict]:
    day_counts = {label: 0 for label in DAY_LABELS}
    for session in sessions.values():
        times = session["tracking_times"]
        if not times:
            continue
        start_time = min(times)
        day_label = DAY_LABELS[start_time.weekday()]
        day_counts[day_label] += 1

    return [
        {
            "day": day,
            "sessions": day_counts[day],
            "is_weekend": day in {"T7", "CN"},
        }
        for day in DAY_LABELS
    ]


def build_platform_split(sessions: dict[str, dict]) -> list[dict]:
    counts = {platform: 0 for platform in PLATFORMS}
    for session in sessions.values():
        platform = session.get("platform", "")
        if platform in counts:
            counts[platform] += 1

    total_sessions = len(sessions)
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "platform": platform,
            "sessions": count,
            "pct": pct((count / total_sessions) * 100) if total_sessions else 0.0,
        }
        for platform, count in ranked
    ]


def build_network_split(sessions: dict[str, dict]) -> list[dict]:
    counts = {network: 0 for network in NETWORKS}
    for session in sessions.values():
        network = session.get("network", "")
        if network in counts:
            counts[network] += 1

    total_sessions = len(sessions)
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "network": network,
            "sessions": count,
            "pct": pct((count / total_sessions) * 100) if total_sessions else 0.0,
        }
        for network, count in ranked
    ]


def build_top_dropoff_events(sessions: dict[str, dict], top_n: int = 10) -> list[dict]:
    event_counts: dict[str, int] = defaultdict(int)

    for session in sessions.values():
        if session["max_step"] >= 7:
            continue
        events = session["events"]
        if not events:
            continue
        last_event = max(events, key=lambda event: event["event_sequence"])
        event_name = last_event.get("event_name", "").strip()
        if event_name:
            event_counts[event_name] += 1

    ranked = sorted(event_counts.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [{"event_name": event_name, "count": count} for event_name, count in ranked]


def parse_event_csv(input_path: Path, output_path: Path) -> dict:
    rows = load_csv(input_path)
    sessions = build_sessions(rows)
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    source_file = input_path.name
    total_sessions = len(sessions)

    funnel_steps = build_funnel_section(sessions, total_sessions)
    funnel = {
        "meta": build_meta(rows, sessions, funnel_steps, source_file, generated_at),
        "funnel_steps": funnel_steps,
        "sessions_by_day": build_sessions_by_day(sessions),
        "platform_split": build_platform_split(sessions),
        "network_split": build_network_split(sessions),
        "top_dropoff_events": build_top_dropoff_events(sessions),
    }

    dashboard = {"funnel": funnel}
    output_path.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse event CSV into funnel dashboard JSON.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    dashboard = parse_event_csv(Path(args.input), Path(args.output))
    meta = dashboard["funnel"]["meta"]
    print(
        f"Wrote {args.output} — "
        f"{meta['total_sessions']} sessions / {meta['total_events']} events / "
        f"{meta['overall_conversion_pct']}% conversion"
    )


if __name__ == "__main__":
    main()
