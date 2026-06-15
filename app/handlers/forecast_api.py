"""Forecast API handler."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from starlette.responses import JSONResponse

from app.services.forecast import ForecastService


async def get_forecast(request) -> JSONResponse:
    """
    GET /api/forecast?period=week&weeks=4
    
    Returns AI-generated forecast based on available data.
    Query params:
    - period: day|week|month (default: week)
    - count: number of periods to forecast (default: 4)
    """
    try:
        # Get query params
        period_type = request.query_params.get("period", "week")
        count = int(request.query_params.get("count", "4"))
        
        # Load existing data
        payment_data = None
        events_data = None
        
        # Try to load from processed JSON files
        data_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        
        # Get latest payment data (most recent file)
        payment_files = list(data_dir.glob("payment_*.json"))
        if payment_files:
            latest_payment = max(payment_files, key=lambda x: x.stat().st_mtime)
            with open(latest_payment, "r", encoding="utf-8") as f:
                payment_data = json.load(f)
        
        events_files = list(data_dir.glob("event_*.json"))
        if events_files:
            latest_event = max(events_files, key=lambda x: x.stat().st_mtime)
            with open(latest_event, "r", encoding="utf-8") as f:
                events_data = json.load(f)
        
        # Generate forecast
        forecast_service = ForecastService(None)
        forecast_result = forecast_service.generate_forecast(
            payment_data, events_data, 
            period_type=period_type, 
            count=count
        )
        
        return JSONResponse(forecast_result)
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Lỗi khi tạo dự báo: {str(e)}"
        }, status_code=500)


async def regenerate_forecast(request) -> JSONResponse:
    """
    POST /api/forecast/regenerate
    
    Regenerate forecast after new data is uploaded.
    """
    try:
        # Same logic as get_forecast but forces regeneration
        payment_data = None
        events_data = None
        
        data_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        
        payment_file = data_dir / "payment_dashboard.json"
        events_file = data_dir / "event_dashboard.json"
        
        if payment_file.exists():
            with open(payment_file, "r", encoding="utf-8") as f:
                payment_data = json.load(f)
        
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)
        
        forecast_service = ForecastService(None)
        forecast_result = forecast_service.generate_forecast(payment_data, events_data)
        
        return JSONResponse({
            "status": "success",
            "message": "Dự báo đã được tạo lại thành công",
            "data": forecast_result
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Lỗi khi tạo lại dự báo: {str(e)}"
        }, status_code=500)
