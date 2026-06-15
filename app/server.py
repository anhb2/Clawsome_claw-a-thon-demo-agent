"""AgentBase application wiring: endpoints, health check, and web routes."""

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    PingStatus,
    RequestContext,
)

from app.data.service import seed_from_project_root
from app.handlers.dashboard_api import chat_with_agent, get_dashboard_data, upload_csv
from app.handlers.forecast_api import get_forecast, regenerate_forecast
from app.handlers.import_data import import_data, list_imported_data, get_latest_data
from app.handlers.invocations import handle_invocation
from app.web.routes import serve_dashboard


def create_app() -> GreenNodeAgentBaseApp:
    seed_from_project_root()

    app = GreenNodeAgentBaseApp()

    @app.entrypoint
    def handler(payload: dict, context: RequestContext) -> dict:
        return handle_invocation(payload, context)

    @app.ping
    def health_check() -> PingStatus:
        return PingStatus.HEALTHY

    app.add_route("/", serve_dashboard, methods=["GET"])
    app.add_route("/dashboard", serve_dashboard, methods=["GET"])
    app.add_route("/dashboard.html", serve_dashboard, methods=["GET"])

    app.add_route("/api/dashboard", get_dashboard_data, methods=["GET"])
    app.add_route("/api/upload", upload_csv, methods=["POST"])
    app.add_route("/api/chat", chat_with_agent, methods=["POST"])
    app.add_route("/api/forecast", get_forecast, methods=["GET"])
    app.add_route("/api/forecast/regenerate", regenerate_forecast, methods=["POST"])
    app.add_route("/api/import", import_data, methods=["POST"])
    app.add_route("/api/import/list", list_imported_data, methods=["GET"])
    app.add_route("/api/import/latest", get_latest_data, methods=["GET"])

    # Legacy alias used by earlier dashboard builds.
    app.add_route("/analyze", upload_csv, methods=["POST"])

    return app
