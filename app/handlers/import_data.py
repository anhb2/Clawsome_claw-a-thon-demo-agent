"""Import data handler with date-time naming."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from starlette.responses import JSONResponse
from starlette.requests import Request

from app.parsers.payment_parser import parse_payment_csv
from app.parsers.event_parser import parse_event_csv


async def import_data(request: Request) -> JSONResponse:
    """
    POST /api/import
    
    Import multiple CSV files with date-time naming.
    Files will be named: payment_YYYYMMDD_HHMMSS.csv, event_YYYYMMDD_HHMMSS.csv
    """
    try:
        # Parse multipart form data
        form = await request.form()
        
        payment_file = form.get("payment")
        events_file = form.get("events")
        
        if not payment_file and not events_file:
            return JSONResponse({
                "status": "error",
                "message": "Vui lòng chọn ít nhất một file CSV để import."
            }, status_code=400)
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Directories
        raw_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        processed_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "status": "success",
            "imported_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "files": []
        }
        
        # Process payment file
        if payment_file:
            try:
                # Read file content
                content = await payment_file.read()
                content_str = content.decode("utf-8")
                
                # Save raw file with timestamp
                raw_filename = f"payment_{timestamp}.csv"
                raw_path = raw_dir / raw_filename
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(content_str)
                
                # Parse and process
                payment_data = parse_payment_csv(content_str)
                
                # Save processed JSON with timestamp
                processed_filename = f"payment_{timestamp}.json"
                processed_path = processed_dir / processed_filename
                with open(processed_path, "w", encoding="utf-8") as f:
                    json.dump(payment_data, f, ensure_ascii=False, indent=2)
                
                # Also save as latest (for backward compatibility)
                latest_path = processed_dir / "payment_dashboard.json"
                with open(latest_path, "w", encoding="utf-8") as f:
                    json.dump(payment_data, f, ensure_ascii=False, indent=2)
                
                results["files"].append({
                    "type": "payment",
                    "raw_file": raw_filename,
                    "processed_file": processed_filename,
                    "status": "success",
                    "records": len(payment_data.get("raw_data", []))
                })
                
            except Exception as e:
                results["files"].append({
                    "type": "payment",
                    "status": "error",
                    "error": str(e)
                })
        
        # Process events file
        if events_file:
            try:
                # Read file content
                content = await events_file.read()
                content_str = content.decode("utf-8")
                
                # Save raw file with timestamp
                raw_filename = f"event_{timestamp}.csv"
                raw_path = raw_dir / raw_filename
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(content_str)
                
                # Parse and process
                events_data = parse_event_csv(content_str)
                
                # Save processed JSON with timestamp
                processed_filename = f"event_{timestamp}.json"
                processed_path = processed_dir / processed_filename
                with open(processed_path, "w", encoding="utf-8") as f:
                    json.dump(events_data, f, ensure_ascii=False, indent=2)
                
                # Also save as latest (for backward compatibility)
                latest_path = processed_dir / "event_dashboard.json"
                with open(latest_path, "w", encoding="utf-8") as f:
                    json.dump(events_data, f, ensure_ascii=False, indent=2)
                
                results["files"].append({
                    "type": "events",
                    "raw_file": raw_filename,
                    "processed_file": processed_filename,
                    "status": "success",
                    "records": len(events_data.get("raw_data", []))
                })
                
            except Exception as e:
                results["files"].append({
                    "type": "events",
                    "status": "error",
                    "error": str(e)
                })
        
        return JSONResponse(results)
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Lỗi khi import data: {str(e)}"
        }, status_code=500)


async def list_imported_data(request: Request) -> JSONResponse:
    """
    GET /api/import/list
    
    List all imported data files with timestamps.
    """
    try:
        processed_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        
        payment_files = sorted(
            processed_dir.glob("payment_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        events_files = sorted(
            processed_dir.glob("event_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        return JSONResponse({
            "status": "success",
            "payment_files": [
                {
                    "filename": f.name,
                    "timestamp": f.stat().st_mtime,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                }
                for f in payment_files
            ],
            "events_files": [
                {
                    "filename": f.name,
                    "timestamp": f.stat().st_mtime,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                }
                for f in events_files
            ]
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Lỗi khi lấy danh sách files: {str(e)}"
        }, status_code=500)


async def get_latest_data(request: Request) -> JSONResponse:
    """
    GET /api/import/latest
    
    Get the latest payment and events data.
    """
    try:
        processed_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        
        payment_files = sorted(
            processed_dir.glob("payment_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        events_files = sorted(
            processed_dir.glob("event_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        payment_data = None
        events_data = None
        
        if payment_files:
            with open(payment_files[0], "r", encoding="utf-8") as f:
                payment_data = json.load(f)
        
        if events_files:
            with open(events_files[0], "r", encoding="utf-8") as f:
                events_data = json.load(f)
        
        return JSONResponse({
            "status": "success",
            "payment": payment_data,
            "events": events_data,
            "payment_file": payment_files[0].name if payment_files else None,
            "events_file": events_files[0].name if events_files else None
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Lỗi khi lấy data mới nhất: {str(e)}"
        }, status_code=500)
