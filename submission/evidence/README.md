# Evidence — Trần Việt Trường (2A202601467)

## Đã tạo cục bộ

- `validate-dashboard.txt`: validator xác nhận `HỢP LỆ: 6/6 panel`.
- `dashboard.html`: dashboard runtime render từ `data/logs.jsonl`.
- `dashboard-runtime.png`: ảnh sáu panel với time range, unit và SLO threshold.

## Cần tài khoản Langfuse để hoàn tất

Không điền trace ID giả. Sau khi có `.env` hợp lệ, chạy checklist sau và thay các ô `<...>` bằng ID/file thật:

1. `python scripts/manage_prompts.py create`.
2. Chạy app với label `baseline`, gọi cùng một input và lưu trace ID vào `trace-v1-id.txt`.
3. Đổi label thành `candidate`, gọi lại input và lưu trace ID vào `trace-v2-id.txt`.
4. Chụp metadata `prompt_name`, `prompt_label`, `prompt_version` của hai trace thành `trace-v1.png`, `trace-v2.png`.
5. `python scripts/manage_prompts.py promote --version 2`, chụp `prompt-promote.png`.
6. `python scripts/manage_prompts.py rollback --version 1`, chụp `prompt-rollback.png`.
7. Chạy ít nhất 10 requests và lưu ảnh danh sách traces thành `traces-list.png`.

Hai trace ID bàn giao cho Dũng:

- baseline/v1: `<TRACE_ID_V1>`
- candidate/v2: `<TRACE_ID_V2>`
