"""AI Forecasting service for Clawsome Agent."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path


class ForecastService:
    """Generate AI-powered forecasts based on historical data."""
    
    def __init__(self, app=None):
        pass
    
    def generate_forecast(self, payment_data: Optional[Dict] = None, 
                         events_data: Optional[Dict] = None,
                         period_type: str = "week",
                         count: int = 4) -> Dict[str, Any]:
        """
        Generate comprehensive forecasts including:
        - User purchase behavior prediction
        - Revenue forecast
        - Strategic recommendations
        - Optimal push notification timing
        
        Args:
            payment_data: Payment data from CSV
            events_data: Events data from CSV
            period_type: 'day', 'week', or 'month'
            count: Number of periods to forecast
        """
        if not payment_data and not events_data:
            return {
                "status": "error",
                "message": "Không có dữ liệu để dự báo. Vui lòng upload payment_raw.csv hoặc events_raw.csv trước."
            }
        
        try:
            # Get current server time
            current_time = datetime.now()
            
            # Extract key metrics from payment data
            revenue_meta = payment_data.get("revenue", {}).get("meta", {}) if payment_data else {}
            behavior_meta = payment_data.get("behavior", {}).get("meta", {}) if payment_data else {}
            
            total_revenue = revenue_meta.get("total_revenue", 0)
            total_tickets = revenue_meta.get("total_tickets", 0)
            aov = revenue_meta.get("aov", 0)
            mpu = behavior_meta.get("mpu", 0)
            at_risk_users = behavior_meta.get("at_risk", 0)
            
            # Generate forecast periods based on period_type
            forecast_periods = self._generate_forecast_periods(period_type, count)
            
            # Generate revenue forecast
            revenue_forecast = self._forecast_revenue(forecast_periods, total_revenue, aov, total_tickets, period_type)
            
            # Generate user behavior forecast
            behavior_forecast = self._forecast_user_behavior(forecast_periods, mpu, at_risk_users, period_type)
            
            # Generate strategic recommendations
            strategic_recommendations = self._generate_strategic_recommendations(
                revenue_forecast, behavior_forecast, current_time, period_type
            )
            
            # Generate push notification recommendations
            push_recommendations = self._generate_push_recommendations(
                behavior_forecast, current_time, period_type
            )
            
            return {
                "status": "success",
                "generated_at": current_time.strftime("%d/%m/%Y %H:%M"),
                "period_type": period_type,
                "forecast_count": count,
                "forecast_periods": forecast_periods,
                "revenue_forecast": revenue_forecast,
                "behavior_forecast": behavior_forecast,
                "strategic_recommendations": strategic_recommendations,
                "push_recommendations": push_recommendations,
                "summary": self._generate_summary(revenue_forecast, behavior_forecast, period_type)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Lỗi khi tạo dự báo: {str(e)}"
            }
    
    def _check_weekend_heavy(self, date: datetime) -> bool:
        """Check if the period contains weekend days."""
        # Simple logic: if period starts Thu-Sun or contains weekend
        weekday = date.weekday()
        return weekday >= 4 or (weekday + 6) % 7 >= 5
    
    def _check_holiday_season(self, date: datetime) -> bool:
        """Check if the period is during holiday season (Vietnam holidays)."""
        month = date.month
        day = date.day
        
        # Major Vietnam holidays
        holiday_periods = [
            (1, 1, 15),   # Tet season (Jan)
            (4, 30, 5, 5),  # Reunification & Labor
            (9, 1, 9, 10),  # National Day
            (12, 20, 12, 31),  # Year end holidays
        ]
        
        for holiday in holiday_periods:
            if len(holiday) == 3:
                if holiday[0] == month and holiday[1] <= day <= holiday[2]:
                    return True
            else:
                if (holiday[0] == month and holiday[1] <= day) or \
                   (holiday[2] == month and day <= holiday[3]):
                    return True
        
        return False
    
    def _generate_forecast_periods(self, period_type: str, count: int) -> list:
        """Generate forecast periods based on period type."""
        periods = []
        current_time = datetime.now()
        
        if period_type == "day":
            for i in range(1, count + 1):
                period_date = current_time + timedelta(days=i)
                periods.append({
                    "index": i,
                    "date": period_date.strftime("%d/%m/%Y"),
                    "day_name": self._get_day_name(period_date.weekday()),
                    "is_weekend": period_date.weekday() >= 5,
                    "is_holiday_season": self._check_holiday_season(period_date)
                })
        elif period_type == "week":
            base_date = current_time + timedelta(days=7 - current_time.weekday())  # Next Monday
            for i in range(count):
                period_start = base_date + timedelta(weeks=i)
                period_end = period_start + timedelta(days=6)
                periods.append({
                    "week": i + 1,
                    "start_date": period_start.strftime("%d/%m/%Y"),
                    "end_date": period_end.strftime("%d/%m/%Y"),
                    "is_weekend_heavy": True,  # Weeks always contain weekends
                    "is_holiday_season": self._check_holiday_season(period_start)
                })
        else:  # month
            for i in range(1, count + 1):
                next_month = current_time.replace(day=1) + timedelta(days=32 * i)
                next_month = next_month.replace(day=1)
                last_day = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                periods.append({
                    "month": i,
                    "month_name": next_month.strftime("%B %Y"),
                    "start_date": next_month.strftime("%d/%m/%Y"),
                    "end_date": last_day.strftime("%d/%m/%Y"),
                    "is_holiday_season": self._check_holiday_season(next_month)
                })
        
        return periods
    
    def _get_day_name(self, weekday: int) -> str:
        """Get Vietnamese day name."""
        days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        return days[weekday] if weekday < 7 else "CN"
    
    def _forecast_revenue(self, periods: list, total_revenue: float, 
                         aov: float, total_tickets: int, period_type: str = "week") -> list:
        """Generate revenue forecast for each period."""
        forecasts = []
        
        # Base revenue calculation based on period type
        if period_type == "day":
            base_period_revenue = total_revenue / 7  # Daily average
            base_period_tickets = total_tickets / 7
        elif period_type == "month":
            base_period_revenue = total_revenue * 4.33  # Monthly average
            base_period_tickets = total_tickets * 4.33
        else:  # week
            base_period_revenue = total_revenue
            base_period_tickets = total_tickets
        
        for i, period in enumerate(periods):
            # Apply seasonal factors
            seasonal_factor = 1.0
            
            # Weekend/day boost
            if period_type == "day":
                if period.get("is_weekend"):
                    seasonal_factor *= 1.35  # Weekend days get 35% boost
                else:
                    seasonal_factor *= 0.85  # Weekdays get less
            elif period.get("is_weekend_heavy"):
                seasonal_factor *= 1.18
            
            # Holiday boost (30-50% increase)
            if period.get("is_holiday_season"):
                seasonal_factor *= 1.40
            
            # Trend factor (slight growth/decline based on period)
            trend_factor = 1.0 + (0.02 if i < 2 else -0.01) * i
            
            # Calculate forecast
            forecast_revenue = base_period_revenue * seasonal_factor * trend_factor
            forecast_tickets = int(base_period_tickets * seasonal_factor * trend_factor)
            forecast_aov = int(forecast_revenue / forecast_tickets) if forecast_tickets > 0 else aov
            
            # Determine trend direction
            if i == 0:
                trend = "Ổn định"
            elif forecast_revenue > base_period_revenue * 1.1:
                trend = "Tăng mạnh"
            elif forecast_revenue > base_period_revenue:
                trend = "Tăng nhẹ"
            elif forecast_revenue < base_period_revenue * 0.9:
                trend = "Giảm mạnh"
            else:
                trend = "Giảm nhẹ"
            
            # Generate reason
            reason = []
            if period_type == "day" and period.get("is_weekend"):
                reason.append("cuối tuần")
            elif period_type == "day" and not period.get("is_weekend"):
                reason.append("ngày thường")
            elif period.get("is_weekend_heavy"):
                reason.append("cuối tuần")
            if period.get("is_holiday_season"):
                reason.append("mùa lễ hội")
            if seasonal_factor > 1.3:
                reason.append("yếu tố mùa vụ cao")
            if trend == "Tăng mạnh":
                reason.append("xu hướng tăng")
            elif trend == "Giảm mạnh":
                reason.append("xu hướng giảm")
            
            # Format period label based on type
            if period_type == "day":
                period_label = f"{period['day_name']} {period['date']}"
                period_id = period["index"]
            elif period_type == "month":
                period_label = period["month_name"]
                period_id = period["month"]
            else:
                period_label = f"T{period['start_date']} - T{period['end_date']}"
                period_id = period["week"]
            
            forecasts.append({
                "period_id": period_id,
                "period_label": period_label,
                "period_full": period_label,
                "forecast_revenue": int(forecast_revenue),
                "forecast_tickets": forecast_tickets,
                "forecast_aov": forecast_aov,
                "trend": trend,
                "trend_direction": "up" if "Tăng" in trend else ("down" if "Giảm" in trend else "flat"),
                "growth_rate": round((seasonal_factor * trend_factor - 1) * 100, 1),
                "reason": " + ".join(reason) if reason else "Biến động theo mùa",
                "confidence": "Cao" if abs(seasonal_factor * trend_factor - 1) < 0.3 else "Trung bình"
            })
        
        return forecasts
    
    def _forecast_user_behavior(self, periods: list, mpu: int, at_risk: int, period_type: str = "week") -> list:
        """Generate user behavior forecast."""
        forecasts = []
        
        # Scale factors based on period type
        if period_type == "day":
            scale_factor = 0.14  # ~1/7 of weekly
        elif period_type == "month":
            scale_factor = 4.33
        else:
            scale_factor = 1.0
        
        for i, period in enumerate(periods):
            # Base activation rate
            base_activation_rate = 0.25  # 25%
            
            # Weekend/day boost for activation
            if period_type == "day":
                if period.get("is_weekend"):
                    base_activation_rate *= 1.5
            elif period.get("is_weekend_heavy"):
                base_activation_rate *= 1.3
            
            # Holiday boost
            if period.get("is_holiday_season"):
                base_activation_rate *= 1.5
            
            # Calculate activated users (scaled by period type)
            activated_users = int(at_risk * base_activation_rate * scale_factor)
            remaining_at_risk = max(0, at_risk - activated_users)
            
            # New user acquisition (based on MPU)
            new_users = int(mpu * 0.15 * scale_factor * (1.2 if (period_type == "day" and period.get("is_weekend")) or period.get("is_weekend_heavy") else 1.0))
            
            # Peak purchase times
            peak_times = self._predict_peak_times(period, period_type)
            
            # Format period label
            if period_type == "day":
                period_label = period["date"]
            elif period_type == "month":
                period_label = f"{period['start_date']} - {period['end_date']}"
            else:
                period_label = f"{period['start_date']} - {period['end_date']}"
            
            forecasts.append({
                "period_id": period.get("week") or period.get("month") or period.get("index", i+1),
                "period": period_label,
                "predicted_activated_users": activated_users,
                "remaining_at_risk": remaining_at_risk,
                "new_users_acquisition": new_users,
                "activation_rate": round(base_activation_rate * 100, 1),
                "peak_purchase_times": peak_times,
                "recommended_actions": self._get_behavior_actions(period, activated_users, new_users, period_type)
            })
        
        return forecasts
    
    def _predict_peak_times(self, period: dict, period_type: str = "week") -> list:
        """Predict peak purchase times for the period."""
        peak_times = []
        
        if period_type == "day":
            # Daily peaks
            if period.get("is_weekend"):
                peak_times.append({
                    "time": "18:00-21:00",
                    "day": period.get("day_name", "Cuối tuần"),
                    "intensity": "Rất cao",
                    "reason": "Cuối tuần evening"
                })
            else:
                peak_times.append({
                    "time": "18:00-21:00",
                    "day": period.get("day_name", "Weekday"),
                    "intensity": "Trung bình",
                    "reason": "Weekday evening"
                })
        elif period_type == "month":
            # Monthly peaks (general)
            peak_times.extend([
                {"time": "18:00-21:00", "day": "Thứ 7-CN", "intensity": "Rất cao", "reason": "Cuối tuần"},
                {"time": "12:00-14:00", "day": "Thứ 3-5", "intensity": "Trung bình", "reason": "Lunch break"}
            ])
        else:
            # Weekly peaks
            peak_times.extend([
                {"time": "18:00-21:00", "day": "Thứ 7", "intensity": "Rất cao", "reason": "Cuối tuần evening"},
                {"time": "14:00-17:00", "day": "Chủ Nhật", "intensity": "Cao", "reason": "Chủ Nhật afternoon"}
            ])
        
        # Holiday boosts
        if period.get("is_holiday_season"):
            peak_times.append({
                "time": "Toàn ngày",
                "day": "Ngày lễ",
                "intensity": "Rất cao",
                "reason": "Mùa lễ hội"
            })
        
        return peak_times
    
    def _get_behavior_actions(self, period: dict, activated: int, new_users: int, period_type: str = "week") -> list:
        """Get recommended actions based on forecast."""
        actions = []
        scale = 1.0 if period_type == "week" else (0.14 if period_type == "day" else 4.33)
        
        if activated > 20 * scale:
            actions.append("Giữ chân users đã active với voucher lần sau")
        if new_users > 15 * scale:
            actions.append("Onboarding campaign cho new users")
        if period_type == "day":
            if period.get("is_weekend"):
                actions.append("Tăng cường marketing cuối tuần")
        elif period.get("is_weekend_heavy"):
            actions.append("Tăng cường marketing cuối tuần")
        if period.get("is_holiday_season"):
            actions.append("Chạy campaign lễ hội đặc biệt")
        
        return actions if actions else ["Duy trì chiến lược hiện tại"]
    
    def _generate_strategic_recommendations(self, revenue_forecast: list, 
                                           behavior_forecast: list,
                                           current_time: datetime,
                                           period_type: str = "week") -> list:
        """Generate strategic business recommendations."""
        recommendations = []
        period_label = "kỳ" if period_type == "day" else ("tháng" if period_type == "month" else "tuần")
        
        # Find highest and lowest revenue periods
        if revenue_forecast:
            highest_period = max(revenue_forecast, key=lambda x: x["forecast_revenue"])
            lowest_period = min(revenue_forecast, key=lambda x: x["forecast_revenue"])
            
            # Revenue strategy
            if highest_period["growth_rate"] > 20:
                recommendations.append({
                    "priority": "P0",
                    "category": "Doanh thu",
                    "title": f"Tận dụng {period_label} {highest_period['period_id']} ({highest_period['period_label']})",
                    "description": f"Doanh thu dự kiến tăng {highest_period['growth_rate']}%. Nên tăng ngân sách marketing, ra mắt phim mới, hoặc chạy promo lớn trong kỳ này.",
                    "expected_impact": f"+{highest_period['growth_rate']}% doanh thu",
                    "timeline": highest_period["period_label"]
                })
            
            if lowest_period["growth_rate"] < -10:
                recommendations.append({
                    "priority": "P1",
                    "category": "Tối ưu",
                    "title": f"Xử lý {period_label} {lowest_period['period_id']} ({lowest_period['period_label']})",
                    "description": f"Doanh thu dự kiến giảm {abs(lowest_period['growth_rate'])}%. Cân nhắc giảm chi phí marketing hoặc chạy retention campaign.",
                    "expected_impact": f"Tiết kiệm {abs(lowest_period['growth_rate'])}% ngân sách",
                    "timeline": lowest_period["period_label"]
                })
        
        # User retention strategy
        total_activated = sum(b["predicted_activated_users"] for b in behavior_forecast)
        if total_activated > 30:
            recommendations.append({
                "priority": "P1",
                "category": "User Retention",
                "title": "Reactivation campaign cho at-risk users",
                "description": f"Dự kiến {total_activated} users sẽ re-activate trong {len(behavior_forecast)} {period_label} tới. Gửi voucher 20K-50K vào khung giờ peak (18:00-21:00) để tối ưu conversion.",
                "expected_impact": f"{total_activated} users reactivated",
                "timeline": f"{len(behavior_forecast)} {period_label} tới"
            })
        
        # Holiday strategy
        holiday_periods = [r for r in revenue_forecast if r.get("reason") and "lễ hội" in r["reason"]]
        if holiday_periods:
            recommendations.append({
                "priority": "P0",
                "category": "Mùa vụ",
                "title": "Chiến lược mùa lễ hội",
                "description": f"Có {len(holiday_periods)} {period_label} trong mùa lễ hội. Nên chuẩn bị early-bird promo, bundle deals, và loyalty rewards để capture demand.",
                "expected_impact": "+30-50% doanh thu so với bình thường",
                "timeline": "Mùa lễ hội"
            })
        
        # Geographic strategy
        recommendations.append({
            "priority": "P2",
            "category": "Địa lý",
            "title": "Tối ưu theo khu vực",
            "description": "Tập trung marketing vào các khu vực có density cao (TP.HCM, Hà Nội) vào cuối tuần. Regional promo cho các tỉnh thành khác vào weekday.",
            "expected_impact": "+15-20% conversion rate",
            "timeline": "Liên tục"
        })
        
        return recommendations
    
    def _generate_push_recommendations(self, behavior_forecast: list, 
                                      current_time: datetime,
                                      period_type: str = "week") -> list:
        """Generate push notification and promotion recommendations."""
        push_recs = []
        period_label = "ngày" if period_type == "day" else ("tháng" if period_type == "month" else "tuần")
        
        for behavior in behavior_forecast:
            # Generate push timing based on peak times
            for peak in behavior["peak_purchase_times"][:2]:  # Top 2 peaks
                push_recs.append({
                    "period_id": behavior["period_id"],
                    "period": behavior["period"],
                    "optimal_send_time": f"{peak['day']} {peak['time']}",
                    "target_audience": "At-risk users" if behavior["predicted_activated_users"] > 10 else "All users",
                    "message_type": "Voucher" if peak["intensity"] == "Rất cao" else "Reminder",
                    "expected_open_rate": f"{25 if peak['intensity'] == 'Rất cao' else 15}%",
                    "expected_conversion": f"{8 if peak['intensity'] == 'Rất cao' else 5}%",
                    "reason": peak["reason"]
                })
        
        # Add special promo recommendations
        if any(b["new_users_acquisition"] > 10 for b in behavior_forecast):
            push_recs.append({
                "period_id": "Liên tục",
                "period": f"{len(behavior_forecast)} {period_label} tới",
                "optimal_send_time": "Thứ 2 10:00",
                "target_audience": "New users",
                "message_type": "Welcome bonus",
                "expected_open_rate": "35%",
                "expected_conversion": "12%",
                "reason": "Onboarding optimization"
            })
        
        return push_recs
    
    def _generate_summary(self, revenue_forecast: list, behavior_forecast: list, period_type: str = "week") -> str:
        """Generate executive summary of forecasts."""
        if not revenue_forecast:
            return "Không có đủ dữ liệu để tạo tóm tắt."
        
        total_forecast_revenue = sum(r["forecast_revenue"] for r in revenue_forecast)
        avg_growth = sum(r["growth_rate"] for r in revenue_forecast) / len(revenue_forecast)
        total_activated = sum(b["predicted_activated_users"] for b in behavior_forecast)
        
        trend = "tăng" if avg_growth > 0 else "giảm"
        period_label = "ngày" if period_type == "day" else ("tháng" if period_type == "month" else "tuần")
        
        summary = (
            f"Dự báo {len(revenue_forecast)} {period_label} tới: Doanh thu tổng dự kiến {total_forecast_revenue/1000000:.1f}Mđ "
            f"với xu hướng {trend} {abs(avg_growth):.1f}% trung bình. "
            f"Dự kiến {total_activated} at-risk users sẽ re-activate. "
        )
        
        # Add key insight
        highest_week = max(revenue_forecast, key=lambda x: x["forecast_revenue"])
        summary += f"Kỳ cao điểm nhất: {highest_week['period_label']} (+{highest_week['growth_rate']}%). "
        
        if any("lễ hội" in r.get("reason", "") for r in revenue_forecast):
            summary += "Mùa lễ hội sẽ mang lại boost doanh thu đáng kể."
        
        return summary
