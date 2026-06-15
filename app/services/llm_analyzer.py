import json

from openai import OpenAI

SYSTEM_PROMPT_TEMPLATE = """Bạn là chuyên gia phân tích dữ liệu.
Nhiệm vụ: Phân tích dataset CSV và trả lời câu hỏi của user.

{context_block}

Quy tắc trả lời:
1. Phân tích ngắn gọn, rõ ràng, có số liệu cụ thể
2. Gợi ý loại biểu đồ phù hợp để visualize
3. Chỉ ra insight quan trọng nhất
4. Trả lời bằng tiếng Việt
5. Trả về JSON với cấu trúc:
{{
  "analysis": "phân tích chi tiết",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "chart_suggestions": [
    {{"type": "bar/line/pie/scatter", "title": "...", "reason": "tại sao dùng chart này"}}
  ]
}}"""


def _build_user_message(summary: dict, question: str) -> str:
    return f"""Dataset:
- Kích thước: {summary["shape_label"]}
- Các cột: {summary["column_label"]}
- Thống kê mô tả:
{summary["describe_text"]}

Câu hỏi: {question}"""


def _parse_llm_json(raw_output: str) -> dict:
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {
            "analysis": raw_output,
            "key_insights": [],
            "chart_suggestions": [],
        }


def analyze_with_llm(
    client: OpenAI,
    model: str,
    summary: dict,
    question: str,
    system_context: str = "",
) -> dict:
    """Ask the LLM to analyze a dataset summary and return structured insights."""
    context_block = (
        f"Ngữ cảnh nghiệp vụ: {system_context}" if system_context else ""
    )
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context_block=context_block)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _build_user_message(summary, question)},
        ],
        temperature=0.3,
    )

    raw_output = response.choices[0].message.content or ""
    return _parse_llm_json(raw_output)
