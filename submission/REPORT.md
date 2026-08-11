# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: D305
- Repository URL: https://github.com/hoangdung04/Day13-K3-D305_HoangManhDung
- Commit SHA cuối:
- Thành viên và vai trò: Hoàng Mạnh Dũng — Logging & PII, Incident/Report; Trường — Tracing & Prompt Version, Dashboard/SLO/Alert.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (`evidence/validate_logs.txt`)
- Tổng số traces:
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID: `evidence/correlation_logs.txt`
- Evidence PII redaction: `evidence/pii_redaction.txt`
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng từ metrics: Feature `refund` có P95 tăng từ 151 ms lên 2653 ms, vượt ngưỡng 2000 ms; error breakdown vẫn rỗng và quality trung bình giữ ở 0.86. Evidence: `evidence/incident_metrics.txt`.
- Trace ID liên quan: Trường bổ sung trace ID/span retrieval tương ứng từ Langfuse.
- Log line/correlation ID liên quan: `req-8dd7cdf6`, `response_sent.latency_ms=2653`; xem `evidence/incident_logs.txt`.
- Root cause: Incident `rag_slow` làm retrieval trong `app/mock_rag.py` chặn 2.5 giây bằng `time.sleep(2.5)`. Mức tăng P95 khoảng 2502 ms khớp với delay được inject.
- Fix action: Tắt `rag_slow` để khôi phục ngay; trong triển khai thực tế cần timeout cho retrieval và fallback/cache thay vì chặn toàn bộ request.
- Preventive measure: Alert khi P95 của feature refund vượt 2000 ms trong một khoảng duy trì; tạo span riêng cho retrieval có correlation ID; chạy canary/load test trước khi phát hành thay đổi retrieval.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hoàng Mạnh Dũng | Correlation ID, structured JSON logging, context metadata, recursive PII redaction; điều tra challenge và tổng hợp report | Bổ sung commit SHA sau khi commit | Dùng correlation ID để nối metric với log; kiểm chứng root cause bằng mức tăng P95 và log cụ thể; redact PII trước khi ghi log |
| Trường | Tracing/prompt version và dashboard/SLO/alert | Trường bổ sung | Trường bổ sung |
