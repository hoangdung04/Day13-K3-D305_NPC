# Chạy dashboard runtime local

Dashboard runtime đọc trực tiếp `data/logs.jsonl` và dùng đúng contract trong `config/dashboard.yaml`.

## Khởi động

Terminal 1 chạy API và tạo log:

```powershell
uvicorn app.main:app --reload --env-file .env
```

Terminal 2 chạy dashboard:

```powershell
uvicorn dashboard_app:app --reload --port 8501
```

Mở `http://127.0.0.1:8501`. Dashboard tự refresh mỗi 30 giây và chỉ đọc dữ liệu trong 60 phút gần nhất.

## Sáu panel

- Latency: P50, P95 và P99 theo `response_sent.latency_ms`.
- Traffic: tổng request và request/phút theo `request_received`.
- Errors: error rate và breakdown theo `request_failed.error_type`.
- Cost: tổng cost và cost theo phút từ `response_sent.cost_usd`.
- Tokens: tổng `tokens_in` và `tokens_out`.
- Quality: trung bình `response_sent.quality_score`.

Mỗi panel hiển thị đơn vị, threshold và trạng thái trong hay ngoài threshold. Contract vẫn phải được kiểm tra riêng:

```powershell
python scripts/validate_dashboard.py
```

Ảnh evidence cần nhìn thấy đủ sáu panel, time range 60 phút, refresh 30 giây, đơn vị và threshold.
