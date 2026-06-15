"""LLM chat over processed dashboard JSON context."""

from __future__ import annotations

import json

from app.config.llm import get_llm_client
from app.data.service import load_dashboard_payload

SYSTEM_PROMPT = """Bạn là ZaloPay Cinema Analytics Agent — chuyên gia phân tích dữ liệu đặt vé phim.

Nhiệm vụ:
- Trả lời câu hỏi của user dựa trên DỮ LIỆU DASHBOARD JSON được cung cấp bên dưới.
- Không bịa số liệu. Nếu dữ liệu chưa có, nói rõ user cần upload CSV tương ứng.
- Trả lời ngắn gọn, có số liệu cụ thể, tiếng Việt.
- Gợi ý hành động kinh doanh khi phù hợp (funnel, churn, doanh thu, segment).

Cấu trúc dữ liệu:
- payment_dashboard: doanh thu (revenue) + hành vi user (behavior/RFM/heatmap)
- event_dashboard: funnel chuyển đổi 7 bước (key "funnel")
"""


def _build_context_block() -> str:
    payload = load_dashboard_payload()
    compact = json.dumps(payload, ensure_ascii=False)
    # Keep context bounded for token limits while preserving metrics.
    if len(compact) > 120_000:
        compact = compact[:120_000] + "...(truncated)"
    return f"DASHBOARD_JSON:\n{compact}"


def answer_dashboard_question(message: str) -> tuple[str, str]:
    client, model = get_llm_client()
    context = _build_context_block()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nCâu hỏi: {message}"},
        ],
        temperature=0.3,
    )
    reply = response.choices[0].message.content or ""
    return reply, model
