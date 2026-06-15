"""Static web routes for the analytics dashboard."""

from starlette.responses import FileResponse

from app.data.paths import DASHBOARD_HTML


async def serve_dashboard(_request):
    return FileResponse(DASHBOARD_HTML)
