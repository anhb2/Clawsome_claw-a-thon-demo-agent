# Clawsome Agent

AI agent tự động hóa phân tích sức khỏe sản phẩm và tình hình kinh doanh — chạy trên [GreenNode AgentBase](https://aiplatform.console.vngcloud.vn).

## Vấn đề

Product Owner và Business team phải tổng hợp dữ liệu từ nhiều nguồn để monitor sức khỏe sản phẩm và tình hình kinh doanh, đồng thời viết báo cáo định kỳ và tìm kiếm nguyên nhân biến động. Công việc này đang khá thủ công và tốn thời gian: mỗi lần báo cáo tốn **4–8 giờ/tuần** chỉ để thu thập, làm sạch số liệu và vẽ biểu đồ. Áp lực deadline khiến phân tích dừng ở mức "số lên/xuống" thay vì trả lời **tại sao** và **nên làm gì tiếp theo**.

## Người dùng mục tiêu

| Đối tượng | Nhu cầu |
|-----------|---------|
| **Product Owner** | Nắm sức khỏe sản phẩm và hành vi người dùng để định hướng action cho team |
| **Business team** | Theo dõi doanh thu và hiệu quả vận hành để ra quyết định kịp thời |

Cả hai cần thông tin chính xác, nhanh, không muốn tốn thời gian xử lý thủ công.

## Cách agent giải quyết

Agent nhận đầu vào là dữ liệu **payment** và **event tracking** thô, sau đó tự động chạy pipeline:

1. Làm sạch dữ liệu
2. Tính chỉ số cốt lõi
3. So sánh với kỳ trước
4. Phân tích nguyên nhân biến động theo nhiều chiều
5. Phân khúc người dùng (RFM, cohort)
6. Dự đoán xu hướng kỳ tới

**Output** là báo cáo có cấu trúc gồm bảng chỉ số, phân tích hành vi, doanh thu, funnel và khuyến nghị action theo độ ưu tiên — hiển thị trên dashboard web hoặc trả lời qua chat.

## Giá trị

- Tiết kiệm **4–8 giờ/tuần** xử lý data thủ công cho PO và Biz team
- Loại bỏ sai sót và không bỏ sót tín hiệu bất thường
- PO nắm sức khỏe sản phẩm để xử lý issue, bug; Biz nắm doanh thu để ra quyết định
- Tất cả từ **một báo cáo duy nhất**, sẵn sàng ngay khi team cần

---

## Prerequisites

- Python 3.10+
- A GreenNode IAM Service Account ([create one here](https://iam.console.vngcloud.vn/service-accounts))

## Setup

1. Create and activate a virtual environment:
   ```bash
   # macOS/Linux:
   python3 -m venv venv && source venv/bin/activate

   # Windows (PowerShell):
   python -m venv venv; venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure credentials for **local development** (choose one method):

   **Option A** - Environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   **Option B** - Config file (already created):
   Edit `.greennode.json` with your `client_id` and `client_secret` from your IAM Service Account.

   > **Note**: When deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically available to the SDK — no manual credential configuration needed in the container.

4. (Optional, for local dev) Create an Agent Identity at https://aiplatform.console.vngcloud.vn/access-control and set `agent_identity` in `.greennode.json` or `GREENNODE_AGENT_IDENTITY` env var. On AgentBase Runtime, this is managed automatically by the runtime system.

## Run Locally

```bash
python3 main.py
```

The agent starts on `http://127.0.0.1:8080`.

Test it:
```bash
curl -X POST http://127.0.0.1:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, agent!"}'
```

**Testing tips** — the SDK extracts metadata from request headers (defined in `greennode_agentbase.runtime.models`):
- If the agent uses **user identity features** (delegated API key, OAuth2 3LO token), pass a user header so credentials resolve correctly:
  `-H "X-GreenNode-AgentBase-User-Id: user-abc"`
- To pass **custom headers** to the agent, use the `X-GreenNode-AgentBase-Custom-` prefix. The SDK collects all headers with this prefix (plus `Authorization`) into `context.request_headers`:
  `-H "X-GreenNode-AgentBase-Custom-My-Key: some-value"`
  Then access in handler: `context.request_headers.get("X-GreenNode-AgentBase-Custom-My-Key")`

Health check:
```bash
curl http://127.0.0.1:8080/health
```

## Project Structure

```
main.py                          # Agent entrypoint
app/
  server.py                      # Routes: dashboard, /api/*, /invocations
  config/llm.py                  # LLM env validation
  data/
    paths.py                     # data/raw, data/processed paths
    service.py                   # Upload CSV, run parsers, load JSON
  parsers/
    payment_parser.py            # payment_raw.csv → payment_dashboard.json
    event_parser.py              # event_raw.csv → event_dashboard.json
  handlers/                      # API request handlers
  services/                      # LLM chat, legacy CSV helpers
  web/
    routes.py                    # Serves dashboard HTML
    static/dashboard.html        # 5-tab analytics UI
data/
  raw/                           # Sample + uploaded CSVs
  processed/                     # Parser output JSON
```

### Dashboard

Open `http://127.0.0.1:8080/` after `python3 main.py`. Upload CSVs via UI.