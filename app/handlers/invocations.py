"""Request handlers for POST /invocations."""

from greennode_agentbase import RequestContext

from app.config.llm import get_llm_client
from app.handlers.response import error_response, success_response
from app.services.csv_parser import build_chart_data, build_dataset_summary, parse_csv
from app.services.llm_analyzer import analyze_with_llm


def handle_invocation(payload: dict, context: RequestContext) -> dict:
    """Route invocation payload to the correct agent workflow."""
    if payload.get("csv_data"):
        return handle_csv_analysis(payload, context)
    if payload.get("message"):
        return handle_chat_message(payload, context)
    return error_response(
        "Payload must include 'csv_data' (CSV analysis) or 'message' (chat).",
        context.session_id,
    )


def handle_csv_analysis(payload: dict, context: RequestContext) -> dict:
    """Parse CSV, run LLM analysis, and return dashboard-ready JSON."""
    csv_data = payload.get("csv_data", "")
    question = payload.get("question", "Phân tích tổng quan dataset này")
    system_context = payload.get("system_context", "")

    if not csv_data.strip():
        return error_response("Thiếu csv_data trong payload.", context.session_id)

    try:
        dataframe = parse_csv(csv_data)
    except Exception as exc:
        return error_response(f"Không thể đọc CSV: {exc}", context.session_id)

    summary = build_dataset_summary(dataframe)
    chart_data = build_chart_data(dataframe, summary["numeric_columns"])

    try:
        client, model = get_llm_client()
    except ValueError as exc:
        return error_response(str(exc), context.session_id)

    try:
        llm_result = analyze_with_llm(
            client=client,
            model=model,
            summary=summary,
            question=question,
            system_context=system_context,
        )
    except Exception as exc:
        return error_response(f"Lỗi khi gọi LLM: {exc}", context.session_id)

    return success_response(
        context.session_id,
        analysis=llm_result.get("analysis", ""),
        key_insights=llm_result.get("key_insights", []),
        chart_suggestions=llm_result.get("chart_suggestions", []),
        chart_data=chart_data,
        summary_stats=summary["summary_stats"],
        meta={
            "rows": summary["rows"],
            "cols": summary["cols"],
            "columns": summary["columns"],
            "model": model,
            "user_id": context.user_id,
        },
    )


def handle_chat_message(payload: dict, context: RequestContext) -> dict:
    """Simple text chat for quick testing without CSV upload."""
    message = payload.get("message", "")

    try:
        client, model = get_llm_client()
    except ValueError as exc:
        return error_response(str(exc), context.session_id)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
        )
        reply = response.choices[0].message.content or ""
    except Exception as exc:
        return error_response(f"LLM request failed: {exc}", context.session_id)

    return success_response(
        context.session_id,
        message=message,
        response=reply,
        model=model,
    )
