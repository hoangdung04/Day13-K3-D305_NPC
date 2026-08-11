# Báo cáo cá nhân — Trần Việt Trường

## Thông tin học viên

- Họ và tên: **Trần Việt Trường**
- Mã học viên: **2A202601467**
- Nhóm: **D305**
- Nhánh thực hiện ban đầu: `truong-tieu-thu`
- Commit phần việc cá nhân: `564df28`

## Phạm vi phụ trách

Trần Việt Trường phụ trách hai mảng của bài Day 13:

1. **Tracing & Prompt Versioning**
   - Tạo prompt `day13-chat` phiên bản baseline v1 và candidate v2.
   - Gắn metadata `prompt_name`, `prompt_label`, `prompt_version` vào trace.
   - Thực hiện promote nhãn `production` sang v2 và rollback về v1.
   - Bàn giao trace ID và ảnh evidence thật, không sử dụng ID giả.
2. **Dashboard, SLO & Alert**
   - Dựng dashboard runtime từ `data/logs.jsonl` theo contract sáu panel.
   - Hoàn thiện latency, traffic, errors, cost, tokens và quality.
   - Bổ sung time range, unit, threshold, SLO, alert rule và runbook.
   - Viết validator test và tài liệu vận hành.

## Kết quả và evidence

| Hạng mục | Kết quả | Evidence |
|---|---|---|
| Prompt baseline v1 | Trace `c95a53a2271d57ab0535d20f328a0517` | `evidence/trace-baseline-v1.jpg` |
| Prompt candidate v2 | Trace `618ed2879e900a2f648166a885225cd5` | `evidence/trace-candidate-v2.jpg` |
| Danh sách trace | 10 trace baseline/candidate có correlation ID | `evidence/trace_ids.json`, `evidence/langfuse-trace-list.jpg` |
| Promote production | Production chuyển sang v2, trace `b6559c26eaecb5633988273e470fc706` | `evidence/prompt_rollback.json` |
| Rollback production | Production trở về v1, trace `a0f6d651fba50cfce86478934dd0f185` | `evidence/prompt_rollback.json`, `evidence/langfuse-rollback-v1.jpg` |
| Dashboard | Đủ 6 nhóm metric, có time range, unit và threshold | `evidence/dashboard-runtime.png`, `evidence/dashboard.html` |
| Dashboard validator | `HỢP LỆ: 6/6 panel` | `evidence/validate_dashboard.txt` |
| SLO và alert | Latency, error, cost, quality; ba alert có runbook | `../config/slo.yaml`, `../config/alert_rules.yaml`, `../docs/alerts.md` |

## File triển khai chính

- `app/prompt_management.py`
- `scripts/manage_prompts.py`
- `scripts/render_dashboard.py`
- `config/dashboard.yaml`
- `config/slo.yaml`
- `config/alert_rules.yaml`
- `docs/PROMPT_VERSIONING.md`
- `docs/DASHBOARD_SETUP.md`
- `docs/alerts.md`
- `tests/test_manage_prompts.py`
- `tests/test_render_dashboard.py`

## Bàn giao cho thành viên Logging/Incident

- Hai trace đại diện v1/v2 và danh sách trace được lưu trong `submission/evidence/`.
- Trace có correlation ID để nối chuỗi **Metrics → Traces → Logs**.
- Dashboard và alert dùng cùng SLO với báo cáo incident của nhóm.
- Phần Logging/PII và kết luận incident do Hoàng Mạnh Dũng phụ trách; báo cáo này chỉ nhận phần công việc của Trần Việt Trường.

## Điều đã học

- Quản lý prompt bằng version/label giúp rollback mà không sửa code ứng dụng.
- Correlation ID và prompt metadata giúp truy ngược từ trace sang log cụ thể.
- Dashboard phải dùng cùng một nguồn dữ liệu và cùng đơn vị với SLO/alert để tránh kết luận sai.
- Evidence cần chứa ID, ảnh runtime và validator thay vì chỉ mô tả bằng văn bản.
