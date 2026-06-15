#!/usr/bin/env python3
"""Parse ZaloPay movie ticket payment CSV into dashboard-ready JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.data.paths import PAYMENT_DASHBOARD_JSON, PAYMENT_RAW_CSV

DEFAULT_INPUT = str(PAYMENT_RAW_CSV)
DEFAULT_OUTPUT = str(PAYMENT_DASHBOARD_JSON)

DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
HOUR_BUCKETS = [8, 10, 12, 14, 16, 18, 20, 22]
HOUR_LABELS = [f"{hour}h" for hour in HOUR_BUCKETS]

RFM_SEGMENT_CONFIG = [
    {
        "segment": "VIP/Champion",
        "segment_key": "VIP",
        "action": "Giữ chân & upsell IMAX/Couple",
        "badge_bg": "#eeedfe",
        "badge_color": "#534ab7",
    },
    {
        "segment": "Trung thành",
        "segment_key": "Regular",
        "action": "Upsell combo bắp nước",
        "badge_bg": "#e6f1fb",
        "badge_color": "#185fa5",
    },
    {
        "segment": "Tiềm năng",
        "segment_key": "Member",
        "action": "Nurture — gửi content phim mới",
        "badge_bg": "#e1f5ee",
        "badge_color": "#0f6e56",
    },
    {
        "segment": "Mới",
        "segment_key": "New",
        "action": "Recall sau 14 ngày đầu",
        "badge_bg": "#faeeda",
        "badge_color": "#854f0b",
    },
]

CHURN_THRESHOLD_DAYS = 45


def parse_num(value: str | int | float | None) -> int:
    """'709,000' | '709000' | 0 | '' → int. Không raise exception."""
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
    """Parse nhiều format datetime. Trả về None nếu lỗi."""
    if not value:
        return None
    for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def pct(value: float) -> float:
    return round(value, 1)


def hour_to_bucket(hour: int, minute: int) -> str:
    """Map purchase time to nearest heatmap hour bucket."""
    total_minutes = hour * 60 + minute
    nearest_hour = HOUR_BUCKETS[0]
    nearest_distance = abs(total_minutes - nearest_hour * 60)
    for bucket_hour in HOUR_BUCKETS[1:]:
        distance = abs(total_minutes - bucket_hour * 60)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_hour = bucket_hour
    return f"{nearest_hour}h"


def load_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            purchase_dt = parse_dt(raw.get("purchase_datetime", ""))
            rows.append(
                {
                    **raw,
                    "num_tickets": parse_num(raw.get("num_tickets")),
                    "unit_price": parse_num(raw.get("unit_price")),
                    "combo_revenue": parse_num(raw.get("combo_revenue")),
                    "total_revenue": parse_num(raw.get("total_revenue")),
                    "voucher_used": parse_num(raw.get("voucher_used")),
                    "purchase_dt": purchase_dt,
                }
            )
    return rows


def _build_revenue_by_day(success: list[dict]) -> list[dict]:
    aggregates = {
        label: {"revenue": 0, "tickets": 0, "orders": 0}
        for label in DAY_LABELS
    }
    for row in success:
        purchase_dt = row["purchase_dt"]
        if not purchase_dt:
            continue
        day_label = DAY_LABELS[purchase_dt.weekday()]
        aggregates[day_label]["revenue"] += row["total_revenue"]
        aggregates[day_label]["tickets"] += row["num_tickets"]
        aggregates[day_label]["orders"] += 1

    return [
        {
            "day": day,
            **aggregates[day],
            "is_weekend": day in {"T7", "CN"},
        }
        for day in DAY_LABELS
    ]


def _build_revenue_by_month(success: list[dict]) -> list[dict]:
    aggregates: dict[str, dict[str, int]] = defaultdict(lambda: {"revenue": 0, "tickets": 0, "orders": 0})
    for row in success:
        purchase_dt = row["purchase_dt"]
        if not purchase_dt:
            continue
        month_key = purchase_dt.strftime("%Y-%m")
        aggregates[month_key]["revenue"] += row["total_revenue"]
        aggregates[month_key]["tickets"] += row["num_tickets"]
        aggregates[month_key]["orders"] += 1

    return [
        {"month": month, **aggregates[month]}
        for month in sorted(aggregates)
    ]


def _build_top_movies(success: list[dict], total_revenue: int) -> list[dict]:
    aggregates: dict[str, dict] = {}
    for row in success:
        movie = row["movie"]
        if movie not in aggregates:
            aggregates[movie] = {
                "movie": movie,
                "genre": row["genre"],
                "revenue": 0,
                "tickets": 0,
                "orders": 0,
            }
        aggregates[movie]["revenue"] += row["total_revenue"]
        aggregates[movie]["tickets"] += row["num_tickets"]
        aggregates[movie]["orders"] += 1

    ranked = sorted(aggregates.values(), key=lambda item: item["revenue"], reverse=True)[:8]
    for item in ranked:
        item["pct"] = pct((item["revenue"] / total_revenue) * 100) if total_revenue else 0.0
    return ranked


def _build_mix(
    success: list[dict],
    total_revenue: int,
    key_field: str,
    label_field: str,
    include_tickets: bool = True,
) -> list[dict]:
    aggregates: dict[str, dict[str, int]] = defaultdict(lambda: {"revenue": 0, "tickets": 0, "orders": 0})
    for row in success:
        key = row[key_field]
        aggregates[key]["revenue"] += row["total_revenue"]
        aggregates[key]["tickets"] += row["num_tickets"]
        aggregates[key]["orders"] += 1

    ranked = sorted(aggregates.items(), key=lambda item: item[1]["revenue"], reverse=True)
    results = []
    for key, values in ranked:
        entry = {
            label_field: key,
            "revenue": values["revenue"],
            "orders": values["orders"],
            "pct": pct((values["revenue"] / total_revenue) * 100) if total_revenue else 0.0,
        }
        if include_tickets:
            entry["tickets"] = values["tickets"]
        results.append(entry)
    return results


def _build_payment_mix(success: list[dict], total_revenue: int) -> list[dict]:
    aggregates: dict[str, dict[str, int]] = defaultdict(lambda: {"revenue": 0, "orders": 0})
    for row in success:
        method = row["payment_method"]
        aggregates[method]["revenue"] += row["total_revenue"]
        aggregates[method]["orders"] += 1

    ranked = sorted(aggregates.items(), key=lambda item: item[1]["revenue"], reverse=True)
    return [
        {
            "method": method,
            "revenue": values["revenue"],
            "orders": values["orders"],
            "pct": pct((values["revenue"] / total_revenue) * 100) if total_revenue else 0.0,
        }
        for method, values in ranked
    ]


def _build_top_cinemas(success: list[dict], total_revenue: int) -> list[dict]:
    aggregates: dict[str, dict[str, int]] = defaultdict(lambda: {"revenue": 0, "orders": 0, "tickets": 0})
    for row in success:
        cinema = row["cinema"]
        aggregates[cinema]["revenue"] += row["total_revenue"]
        aggregates[cinema]["orders"] += 1
        aggregates[cinema]["tickets"] += row["num_tickets"]

    ranked = sorted(aggregates.items(), key=lambda item: item[1]["revenue"], reverse=True)[:8]
    return [
        {
            "cinema": cinema,
            "revenue": values["revenue"],
            "orders": values["orders"],
            "tickets": values["tickets"],
            "pct": pct((values["revenue"] / total_revenue) * 100) if total_revenue else 0.0,
        }
        for cinema, values in ranked
    ]


def _build_day_type_split(success: list[dict], total_revenue: int) -> list[dict]:
    aggregates: dict[str, int] = defaultdict(int)
    for row in success:
        aggregates[row["day_type"]] += row["total_revenue"]

    ranked = sorted(aggregates.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "type": day_type,
            "revenue": revenue,
            "pct": pct((revenue / total_revenue) * 100) if total_revenue else 0.0,
        }
        for day_type, revenue in ranked
    ]


def build_behavior_section(
    success: list[dict],
    total_revenue: int,
    source_file: str,
    generated_at: str,
) -> dict:
    user_orders: dict[str, list[datetime]] = defaultdict(list)
    user_revenue: dict[str, int] = defaultdict(int)
    purchase_dates: list[datetime] = []

    for row in success:
        user_id = row["user_id"]
        user_revenue[user_id] += row["total_revenue"]
        if row["purchase_dt"]:
            user_orders[user_id].append(row["purchase_dt"])
            purchase_dates.append(row["purchase_dt"])

    total_orders = len(success)
    mpu = len(user_orders)
    new_users = sum(1 for orders in user_orders.values() if len(orders) == 1)
    avg_frequency = round(total_orders / mpu, 2) if mpu else 0.0

    max_date = max(purchase_dates) if purchase_dates else None
    at_risk = 0
    if max_date:
        for orders in user_orders.values():
            last_purchase = max(orders)
            if (max_date - last_purchase).days >= CHURN_THRESHOLD_DAYS:
                at_risk += 1

    return {
        "meta": {
            "mpu": mpu,
            "new_users": new_users,
            "avg_frequency": avg_frequency,
            "at_risk": at_risk,
            "churn_threshold_days": CHURN_THRESHOLD_DAYS,
            "source": source_file,
            "generated_at": generated_at,
        },
        "rfm_segments": _build_rfm_segments(success, total_revenue),
        "heatmap": _build_heatmap(success),
    }


def _build_rfm_segments(success: list[dict], total_revenue: int) -> list[dict]:
    segment_users: dict[str, set[str]] = defaultdict(set)
    segment_revenue: dict[str, int] = defaultdict(int)

    for row in success:
        segment_key = row["user_segment"]
        segment_users[segment_key].add(row["user_id"])
        segment_revenue[segment_key] += row["total_revenue"]

    segments = []
    for config in RFM_SEGMENT_CONFIG:
        key = config["segment_key"]
        users = len(segment_users.get(key, set()))
        revenue = segment_revenue.get(key, 0)
        segments.append(
            {
                "segment": config["segment"],
                "segment_key": key,
                "users": users,
                "avg_revenue": round(revenue / users) if users else 0,
                "total_revenue": revenue,
                "pct_revenue": pct((revenue / total_revenue) * 100) if total_revenue else 0.0,
                "action": config["action"],
                "badge_bg": config["badge_bg"],
                "badge_color": config["badge_color"],
            }
        )
    return segments


def _build_heatmap(success: list[dict]) -> list[dict]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for hour_label in HOUR_LABELS:
        for day_label in DAY_LABELS:
            counts[(hour_label, day_label)] = 0

    for row in success:
        purchase_dt = row["purchase_dt"]
        if not purchase_dt:
            continue
        hour_label = hour_to_bucket(purchase_dt.hour, purchase_dt.minute)
        day_label = DAY_LABELS[purchase_dt.weekday()]
        counts[(hour_label, day_label)] += 1

    heatmap = []
    for hour_label in HOUR_LABELS:
        for day_label in DAY_LABELS:
            heatmap.append(
                {
                    "hour": hour_label,
                    "day": day_label,
                    "value": counts[(hour_label, day_label)],
                }
            )
    return heatmap


def parse_payment_csv(input_path: Path, output_path: Path) -> dict:
    rows = load_csv(input_path)
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    source_file = input_path.name

    total_rows = len(rows)
    success = [row for row in rows if row.get("status") == "Success"]
    total_refunded = sum(1 for row in rows if row.get("status") == "Refunded")
    total_failed = sum(1 for row in rows if row.get("status") == "Failed")
    cancel_rate = pct((total_refunded / total_rows) * 100) if total_rows else 0.0

    total_revenue = sum(row["total_revenue"] for row in success)
    total_orders = len(success)
    voucher_orders = sum(1 for row in success if row["voucher_used"] > 0)
    combo_orders = sum(1 for row in success if row["combo_revenue"] > 0)

    revenue = {
        "meta": {
            "total_revenue": total_revenue,
            "total_tickets": sum(row["num_tickets"] for row in success),
            "total_orders": total_orders,
            "aov": round(total_revenue / total_orders) if total_orders else 0,
            "cancel_rate": cancel_rate,
            "voucher_rate": pct((voucher_orders / total_orders) * 100) if total_orders else 0.0,
            "voucher_discount_total": sum(row["voucher_used"] for row in success if row["voucher_used"] > 0),
            "combo_rate": pct((combo_orders / total_orders) * 100) if total_orders else 0.0,
            "combo_revenue_total": sum(row["combo_revenue"] for row in success),
            "source": source_file,
            "generated_at": generated_at,
        },
        "revenue_by_day": _build_revenue_by_day(success),
        "revenue_by_month": _build_revenue_by_month(success),
        "top_movies": _build_top_movies(success, total_revenue),
        "ticket_type_mix": _build_mix(success, total_revenue, key_field="ticket_type", label_field="type"),
        "payment_mix": _build_payment_mix(success, total_revenue),
        "genre_mix": _build_mix(success, total_revenue, key_field="genre", label_field="genre", include_tickets=False),
        "top_cinemas": _build_top_cinemas(success, total_revenue),
        "day_type_split": _build_day_type_split(success, total_revenue),
    }

    behavior = build_behavior_section(success, total_revenue, source_file, generated_at)

    dashboard = {
        "meta": {
            "generated_at": generated_at,
            "source_file": source_file,
            "total_rows": total_rows,
            "total_success": len(success),
            "total_refunded": total_refunded,
            "total_failed": total_failed,
            "cancel_rate": cancel_rate,
        },
        "revenue": revenue,
        "behavior": behavior,
    }

    output_path.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse payment CSV into dashboard JSON.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    dashboard = parse_payment_csv(Path(args.input), Path(args.output))
    print(
        f"Wrote {args.output} — "
        f"{dashboard['meta']['total_success']} success / {dashboard['meta']['total_rows']} rows"
    )


if __name__ == "__main__":
    main()
