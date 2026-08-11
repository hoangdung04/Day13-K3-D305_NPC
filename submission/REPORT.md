# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: D305
- Repository URL: https://github.com/hoangdung04/Day13-K3-D305_NPC
- Commit SHA nộp: lấy từ HEAD sau commit/push cuối bằng `git rev-parse HEAD`; commit CP0/CP1 đã push: `689c888`.
- Thành viên và vai trò: Hoàng Mạnh Dũng (`2A202601213`) — Logging & PII, Incident/Report; Trần Việt Trường (`2A202601467`) — Tracing & Prompt Version, Dashboard/SLO/Alert.

> **Ghi chú cho mentor:** Báo cáo và bảng evidence cá nhân của **Trần Việt Trường — 2A202601467** nằm tại [`TRAN_VIET_TRUONG_2A202601467.md`](TRAN_VIET_TRUONG_2A202601467.md). Phần triển khai gốc nằm ở commit `564df28`; commit nộp cuối bổ sung ghi chú này để việc chấm đóng góp từng thành viên rõ ràng.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (`evidence/validate_logs.txt`)
- Tổng số traces có evidence: 22 (10 baseline/candidate, 2 đổi production/rollback và 10 challenge baseline/incident); ảnh danh sách tại `evidence/langfuse-trace-list.jpg`.
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: Local `http://127.0.0.1:8501`; evidence `evidence/dashboard-runtime.png`

## 3. Logging và tracing

- Evidence correlation ID: `evidence/correlation_logs.txt`
- Evidence PII redaction: `evidence/pii_redaction.txt`
- Evidence trace waterfall: `evidence/langfuse-waterfall.jpg`, `evidence/challenge_trace.json` và `evidence/trace_waterfall.txt`.
- Giải thích một span đáng chú ý: trace `599082bcff488877d19bb7182a6ade01` có generation `run` dài 2659 ms; span con `rag_retrieval` dài 2507 ms, chiếm khoảng 94% thời gian trace và xác nhận retrieval là nút thắt.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: v1, labels `baseline` và `production` sau rollback.
- Version/label candidate: v2, label `candidate`.
- Trace ID đại diện: v1/baseline `c95a53a2271d57ab0535d20f328a0517` (`evidence/trace-baseline-v1.jpg`); v2/candidate `618ed2879e900a2f648166a885225cd5` (`evidence/trace-candidate-v2.jpg`). Danh sách đủ 10 trace nằm trong `evidence/trace_ids.json`.
- Bằng chứng đổi label hoặc rollback: `evidence/langfuse-rollback-v1.jpg` và `evidence/prompt_rollback.json`; production được chuyển sang v2 (trace `b6559c26eaecb5633988273e470fc706`) rồi rollback về v1 (trace `a0f6d651fba50cfce86478934dd0f185`).

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel`; xem `evidence/validate_dashboard.txt`.
- Evidence dashboard: `evidence/dashboard-runtime.png`
- SLO đã chọn và lý do: P95 latency ≤ 3000 ms, error rate ≤ 2%, daily cost ≤ 2.5 USD và quality trung bình ≥ 0.75; các ngưỡng bám theo contract dashboard và phản ánh trực tiếp trải nghiệm người dùng.
- Alert rules và runbook: `../config/alert_rules.yaml` và `../docs/alerts.md`; gồm HighP95Latency, HighErrorRate và LowQualityScore.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng từ metrics: Feature `refund` có P95 tăng từ 1063 ms ở lượt baseline lên 2652 ms sau khi bật `rag_slow`, vượt ngưỡng 2000 ms; error breakdown vẫn rỗng và quality trung bình giữ ở 0.86. Evidence đầy đủ: `evidence/challenge_trace.json`.
- Trace ID liên quan: `599082bcff488877d19bb7182a6ade01`; waterfall gồm `run` 2659 ms và `rag_retrieval` 2507 ms.
- Log line/correlation ID liên quan: `req-2d1c76d6`, `response_sent.latency_ms=2652`; có thể nối log với trace qua metadata `correlation_id`. Evidence cũ của lần chạy local vẫn được giữ tại `evidence/incident_logs.txt`.
- Root cause: Incident `rag_slow` làm retrieval trong `app/mock_rag.py` chặn 2.5 giây bằng `time.sleep(2.5)`. Mức tăng P95 khoảng 2502 ms khớp với delay được inject.
- Fix action: Tắt `rag_slow` để khôi phục ngay; trong triển khai thực tế cần timeout cho retrieval và fallback/cache thay vì chặn toàn bộ request.
- Preventive measure: Alert khi P95 của feature refund vượt 2000 ms trong một khoảng duy trì; tạo span riêng cho retrieval có correlation ID; chạy canary/load test trước khi phát hành thay đổi retrieval.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hoàng Mạnh Dũng (`2A202601213`) | Correlation ID, structured JSON logging, context metadata, recursive PII redaction; điều tra challenge và tổng hợp report | `689c888`, `4855eb2` | Dùng correlation ID để nối metrics với logs; kiểm chứng root cause bằng mức tăng P95 và log cụ thể; redact PII trước khi ghi log |
| Trần Việt Trường (`2A202601467`) | Correlation ID trong trace metadata; prompt v1/v2 và rollback; dashboard runtime 6 panel; SLO, alert và runbook | `564df28` và merge commit trên nhánh nộp | Nối trace với log bằng correlation ID; chuyển dashboard contract thành dashboard runtime; thiết kế alert theo triệu chứng và SLO |

Chi tiết phần việc, trace ID và evidence của Trần Việt Trường: [`TRAN_VIET_TRUONG_2A202601467.md`](TRAN_VIET_TRUONG_2A202601467.md).
