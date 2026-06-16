"""Simple AI Forecast using GreenNode MAAS LLM - Optimized for speed."""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class SimpleAIForecastService:
    """Fast AI forecast with minimal prompt."""
    
    def __init__(self):
        self.api_key = os.environ.get("LLM_API_KEY") or os.environ.get("MAAS_API_KEY")
        self.base_url = os.environ.get("LLM_BASE_URL")
        self.model = os.environ.get("LLM_MODEL", "qwen/qwen3-5-27b")
        
        self.client = None
        if OpenAI and self.api_key and self.base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            print(f"✅ LLM Client initialized: {self.model} @ {self.base_url}")
        else:
            print("❌ LLM Client NOT initialized")
    
    def generate_forecast(self, payment_data: Optional[Dict], events_data: Optional[Dict],
                         period_type: str = "week", count: int = 4) -> Dict[str, Any]:
        """Generate forecast using LLM or fallback."""
        
        if not payment_data:
            return self._error("Không có payment data")
        
        # Extract key metrics
        rev_meta = payment_data.get("revenue", {}).get("meta", {})
        beh_meta = payment_data.get("behavior", {}).get("meta", {})
        
        total_rev = rev_meta.get("total_revenue", 0)
        total_tickets = rev_meta.get("total_tickets", 0)
        mpu = beh_meta.get("mpu", 0)
        at_risk = beh_meta.get("at_risk", 0)
        
        # Try AI forecast first
        if self.client:
            try:
                print(f"🤖 Calling LLM with data: revenue={total_rev:,}, tickets={total_tickets:,}")
                ai_result = self._call_llm_forecast(total_rev, total_tickets, mpu, at_risk, period_type, count)
                if ai_result and ai_result.get("status") == "success":
                    print(f"✅ AI forecast successful")
                    return ai_result
            except Exception as e:
                print(f"⚠️ AI forecast failed: {e}, using fallback")
        
        # Fallback to rule-based
        print("📊 Using rule-based forecast")
        from app.services.forecast import ForecastService
        return ForecastService().generate_forecast(payment_data, events_data, period_type, count)
    
    def _call_llm_forecast(self, revenue: int, tickets: int, mpu: int, at_risk: int,
                          period_type: str, count: int) -> Dict[str, Any]:
        """Call LLM with minimal prompt for fast response."""
        
        period_label = "ngày" if period_type == "day" else ("tháng" if period_type == "month" else "tuần")
        
        prompt = f"""Phân tích nhanh và trả về JSON:
- Doanh thu hiện tại: {revenue/1000000:.1f}Mđ
- Vé bán: {tickets:,}
- MPU: {mpu:,}
- At-risk: {at_risk:,}

Dự báo {count} {period_label} tới. Trả về CHỈ JSON:
{{
  "summary": "Tóm tắt 2 câu",
  "revenue_forecast": [{{"period_id": 1, "period_label": "Tuần 1", "forecast_revenue": 700000000, "forecast_tickets": 5000, "trend": "Tăng", "growth_rate": 3.2, "reason": "Cuối tuần", "confidence": "Cao", "period_full": "Tuần 1: 22/06-28/06", "forecast_aov": 140000, "trend_direction": "up"}}],
  "behavior_forecast": [{{"period_id": 1, "period": "22/06-28/06", "predicted_activated_users": 150, "remaining_at_risk": 900, "new_users_acquisition": 50, "activation_rate": 13.4, "peak_purchase_times": [{{"time": "18:00-21:00", "day": "Thứ 7", "intensity": "Cao"}}], "recommended_actions": ["Gửi voucher"]}}],
  "strategic_recommendations": [{{"priority": "P0", "category": "Doanh thu", "title": "Tăng marketing", "description": "Tăng ngân sách T6-T7", "expected_impact": "+15%", "timeline": "1 tuần"}}],
  "push_recommendations": [{{"period_id": 1, "period": "22/06-28/06", "optimal_send_time": "Thứ 6 18:00", "target_audience": "At-risk", "message_type": "Voucher", "expected_open_rate": "25%", "expected_conversion": "8%", "reason": "Peak time"}}]
}}
JSON thuần, không markdown."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000,
            reasoning_effort="low"
        )
        
        content = response.choices[0].message.content or response.choices[0].message.reasoning or ""
        
        # Parse JSON
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1] if "```" in cleaned else cleaned
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(cleaned)
            print(f"✅ Parsed AI response: {len(data.get('revenue_forecast', []))} forecasts")
            
            return {
                "status": "success",
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "period_type": period_type,
                "forecast_count": count,
                "summary": data.get("summary", ""),
                "revenue_forecast": data.get("revenue_forecast", []),
                "behavior_forecast": data.get("behavior_forecast", []),
                "strategic_recommendations": data.get("strategic_recommendations", []),
                "push_recommendations": data.get("push_recommendations", [])
            }
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Raw response: {content[:200]}")
            return {"status": "error", "message": "Không parse được JSON từ AI"}
    
    def _error(self, message: str) -> Dict[str, Any]:
        return {"status": "error", "message": message}
