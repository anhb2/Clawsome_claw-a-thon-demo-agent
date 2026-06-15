"""HTTP handlers for dashboard upload, data API, and AI chat."""

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.data.service import (
    load_dashboard_payload,
    process_event_csv,
    process_payment_csv,
    save_event_csv,
    save_payment_csv,
    seed_from_project_root,
)
from app.handlers.response import error_response, success_response
from app.services.dashboard_chat import answer_dashboard_question


async def get_dashboard_data(_request: Request) -> JSONResponse:
    seed_from_project_root()
    payload = load_dashboard_payload()
    return JSONResponse(payload)


async def upload_csv(request: Request) -> JSONResponse:
    form = await request.form()
    result: dict = {"payment": None, "events": None, "errors": []}

    payment_file = form.get("payment")
    events_file = form.get("events")

    # Backward-compatible single-file upload from older dashboard UI.
    legacy_file = form.get("file")
    legacy_type = form.get("type")
    if legacy_file is not None and not payment_file and not events_file:
        if legacy_type == "events":
            events_file = legacy_file
        else:
            payment_file = legacy_file

    try:
        if payment_file is not None and getattr(payment_file, "filename", ""):
            save_payment_csv(await payment_file.read())
            result["payment"] = process_payment_csv()

        if events_file is not None and getattr(events_file, "filename", ""):
            save_event_csv(await events_file.read())
            result["events"] = process_event_csv()

        if not result["payment"] and not result["events"]:
            return JSONResponse(
                {"status": "error", "error": "Cần upload ít nhất một file CSV (payment hoặc events)."},
                status_code=400,
            )
    except Exception as exc:
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=400)

    return JSONResponse({"status": "success", **result})


async def chat_with_agent(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(error_response("Invalid JSON body.", None), status_code=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JSONResponse(error_response("Thiếu message trong payload.", None), status_code=400)

    try:
        reply, model = answer_dashboard_question(message)
    except ValueError as exc:
        return JSONResponse(error_response(str(exc), None), status_code=400)
    except Exception as exc:
        return JSONResponse(error_response(f"LLM request failed: {exc}", None), status_code=500)

    return JSONResponse(success_response(None, response=reply, model=model))
