"""AI Forecasting service using GreenNode MAAS LLM."""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class AIForecastService:
    """Generate AI-powered forecasts using GreenNode MAAS LLM."""
    
    def __init__(self):
        self.api_key = os.environ.get("LLM_API_KEY") or os.environ.get("MAAS_API_KEY")
        self.base_url = os.environ.get("LLM_BASE_URL", "https://llm.api.vngcloud.vn/v1")
        self.model = os.environ.get("LLM_MODEL", "qwen/qwen3-5-27b")
        
        self.client = None
        if OpenAI and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    def generate_ai_forecast(self, payment_data: Optional[Dict] = None, 
                             events_data: Optional[Dict] = None,
                             period_type: str = "week",
                             count: int = 4) -> Dict[str, Any]:
        """
        Generate comprehensive AI forecasts by calling the LLM with CSV data.
        
        Args:
            payment_data: Payment data from CSV
            events_data: Events data from CSV
            period_type: 'day', 'week', or 'month'
            count: Number of periods to forecast
            
        Returns:
            AI-generated forecast with revenue, behavior, and recommendations
        """
        if not payment_data and not events_data:
            return {
                "status": "error",
                "message": "Không có dữ liệu để dự báo. Vui lòng upload file CSV trước."
            }
        
        if not self.client:
            return {
                "status": "error",
                "message": "LLM API chưa được cấu hình. Vui lòng kiểm tra LLM_API_KEY trong .env"
            }
        
        try:
            # Prepare data summary for the prompt
            data_summary = self._prepare_data_summary(payment_data, events_data)
            
            # Build the prompt
            prompt = self._build_forecast_prompt(data_summary, period_type, count)
            
            # Call LLM
            response = self._call_llm(prompt)
            
            # Parse and structure the response
            forecast_data = self._parse_llm_response(response, period_type, count)
            
            return {
                "status": "success",
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "period_type": period_type,
                "forecast_count": count,
                "summary": forecast_data.get("summary", ""),
                "revenue_forecast": forecast_data.get("revenue_forecast", []),
                "behavior_forecast": forecast_data.get("behavior_forecast", []),
                "strategic_recommendations": forecast_data.get("strategic_recommendations", []),
                "push_recommendations": forecast_data.get("push_recommendations", [])
            }
            
        except Exception as e:
            print(f"AI Forecast error: {str(e)}")
            # Fallback to rule-based forecast
            from app.services.forecast import ForecastService
            fallback_service = ForecastService()
            return fallback_service.generate_forecast(payment_data, events_data, period_type, count)
    
    def _prepare_data_summary(self, payment_data: Dict, events_data: Dict) -> str:
        """Prepare a concise summary of the data for the LLM prompt."""
        summary_parts = []
        
        if payment_data:
            revenue = payment_data.get("revenue", {})
            behavior = payment_data.get("behavior", {})
            
            rev_meta = revenue.get("meta", {})
            beh_meta = behavior.get("meta", {})
            
            summary_parts.append("=== DỮ LIỆU DOANH THU ===")
            summary_parts.append(f"• Tổng doanh thu: {rev_meta.get('total_revenue', 0):,}đ")
            summary_parts.append(f"• Tổng vé bán: {rev_meta.get('total_tickets', 0):,}")
            summary_parts.append(f"• AOV (Average Order Value): {rev_meta.get('aov', 0):,}đ")
            summary_parts.append(f"• Tỷ lệ hoàn vé: {rev_meta.get('cancel_rate', 0)}%")
            if rev_meta.get('wow_growth'):
                summary_parts.append(f"• Tăng trưởng WoW: {rev_meta.get('wow_growth')}%")
            
            summary_parts.append("\n=== DỮ LIỆU HÀNH VI NGƯỜI DÙNG ===")
            summary_parts.append(f"• MPU (Monthly Paying Users): {beh_meta.get('mpu', 0):,}")
            summary_parts.append(f"• User mới: {beh_meta.get('new_users', 0):,}")
            summary_parts.append(f"• At-risk users: {beh_meta.get('at_risk', 0):,}")
            summary_parts.append(f"• Tần suất mua trung bình: {beh_meta.get('avg_frequency', 0)}×/tháng")
            
            # RFM segments
            if "rfm_segments" in behavior:
                summary_parts.append("\n• Phân khúc RFM:")
                for seg in behavior["rfm_segments"][:5]:
                    summary_parts.append(f"  - {seg['segment']}: {seg['users']} users, avg_rev: {seg['avg_revenue']:,}đ")
        
        if events_data:
            funnel = events_data.get("funnel", {})
            fun_meta = funnel.get("meta", {})
            
            summary_parts.append("\n=== DỮ LIỆU FUNNEL ===")
            summary_parts.append(f"• Tổng sessions: {fun_meta.get('total_sessions', 0):,}")
            summary_parts.append(f"• Tổng events: {fun_meta.get('total_events', 0):,}")
            summary_parts.append(f"• Overall conversion: {fun_meta.get('overall_conversion_pct', 0)}%")
            summary_parts.append(f"• Nút thắt lớn nhất: Bước {fun_meta.get('biggest_dropoff_step')} - {fun_meta.get('biggest_dropoff_screen')} (drop-off: {fun_meta.get('biggest_dropoff_pct')}%)")
            
            # Funnel steps
            if "funnel_steps" in funnel:
                summary_parts.append("\n• Chi tiết funnel:")
                for step in funnel["funnel_steps"][:7]:
                    summary_parts.append(f"  - Bước {step['step']} ({step['screen_name']}): reach {step['reach_pct']}%, conversion {step['step_conversion_pct']}%, drop {step['dropoff_pct']}%")
        
        return "\n".join(summary_parts)
    
    def _build_forecast_prompt(self, data_summary: str, period_type: str, count: int) -> str:
        """Build the LLM prompt for forecasting."""
        period_label = "ngày" if period_type == "day" else ("tháng" if period_type == "month" else "tuần")
        
        prompt = f"""Bạn là AI Agent phân tích dữ liệu cho một app bán vé phim. Nhiệm vụ: mỗi tuần và mỗi tháng tự động đọc dữ liệu giao dịch (payment) và sự kiện (event tracking), tính toán các chỉ số sức khỏe sản phẩm, phát hiện bất thường, giải thích nguyên nhân biến động, phân tích hành vi người dùng và dự đoán hành vi tiếp theo để đề xuất thời điểm acquire / recall / remind nhằm tăng số vé bán và MPU.

DỮ LIỆU HIỆN TẠI:
{data_summary}

YÊU CẦU: Dự báo {count} {period_label} tới với format JSON chính xác theo schema dưới đây:

{{
  "summary": "Tóm tắt executive 2-3 câu về xu hướng chính và insight quan trọng nhất",
  "revenue_forecast": [
    {{
      "period_id": 1,
      "period_label": "T1 16/06 - T7 22/06",
      "period_full": "Tuần 1: 16/06/2026 - 22/06/2026",
      "forecast_revenue": 125000000,
      "forecast_tickets": 1500,
      "forecast_aov": 83333,
      "trend": "Tăng nhẹ",
      "trend_direction": "up",
      "growth_rate": 5.2,
      "reason": "Cuối tuần + phim mới ra mắt",
      "confidence": "Cao"
    }}
  ],
  "behavior_forecast": [
    {{
      "period_id": 1,
      "period": "16/06/2026 - 22/06/2026",
      "predicted_activated_users": 45,
      "remaining_at_risk": 120,
      "new_users_acquisition": 28,
      "activation_rate": 27.3,
      "peak_purchase_times": [
        {{"time": "18:00-21:00", "day": "Thứ 7", "intensity": "Rất cao", "reason": "Cuối tuần evening"}}
      ],
      "recommended_actions": ["Gửi voucher 20K cho at-risk users vào Thứ 6 18:00"]
    }}
  ],
  "strategic_recommendations": [
    {{
      "priority": "P0",
      "category": "Doanh thu",
      "title": "Tận dụng cuối tuần tăng trưởng",
      "description": "Doanh thu cuối tuần dự kiến tăng 18%. Nên tăng ngân sách marketing T6-T7.",
      "expected_impact": "+18% doanh thu",
      "timeline": "Tuần 1-2"
    }}
  ],
  "push_recommendations": [
    {{
      "period_id": 1,
      "period": "16/06 - 22/06",
      "optimal_send_time": "Thứ 6 18:00",
      "target_audience": "At-risk users",
      "message_type": "Voucher",
      "expected_open_rate": "25%",
      "expected_conversion": "8%",
      "reason": "Peak time trước cuối tuần"
    }}
  ]
}}

HƯỚNG DẪN:
1. Phân tích xu hướng từ dữ liệu hiện tại (WoW growth, conversion rate, at-risk users)
2. Dự báo doanh thu dựa trên: yếu tố mùa vụ (cuối tuần, lễ hội), xu hướng hiện tại, AOV
3. Dự đoán hành vi: activation rate, new users, peak times dựa trên heatmap và RFM
4. Đề xuất chiến lược P0 (urgent), P1 (important), P2 (nice-to-have)
5. Recommend push notification timing dựa trên peak purchase times

CHỈ TRẢ VỀ JSON THUẦN, KHÔNG CÓ TEXT KHÁC."""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the GreenNode MAAS LLM API."""
        if not self.client:
            raise Exception("LLM client not initialized")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=8000,
                reasoning_effort="low"
            )
            
            # Get content or reasoning (some models return reasoning instead)
            content = response.choices[0].message.content
            if not content:
                content = response.choices[0].message.reasoning
            
            result = content or ""
            print(f"✅ LLM call successful. Tokens: {response.usage.completion_tokens}, Content length: {len(result)}")
            return result
            
        except Exception as e:
            print(f"❌ LLM call failed: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str, period_type: str, count: int) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            # Clean up response (remove markdown code blocks if present)
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            cleaned = cleaned.rstrip("```").strip()
            
            data = json.loads(cleaned)
            
            # Validate required fields
            required = ["summary", "revenue_forecast", "behavior_forecast", 
                       "strategic_recommendations", "push_recommendations"]
            for field in required:
                if field not in data:
                    data[field] = [] if isinstance(data.get(field), list) else ""
            
            return data
            
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response: {response[:200]}...")
            # Return empty structure
            return {
                "summary": "AI đang phân tích dữ liệu...",
                "revenue_forecast": [],
                "behavior_forecast": [],
                "strategic_recommendations": [],
                "push_recommendations": []
            }
