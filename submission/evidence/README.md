# Evidence nhóm D305

## Thành viên

- Hoàng Mạnh Dũng — Logging & PII, Incident/Report.
- Trần Việt Trường (`2A202601467`) — Tracing & Prompt Version, Dashboard/SLO/Alert.

## Logging và PII

- `validate_logs.txt`: validator đạt 100/100.
- `correlation_logs.txt`: correlation ID và metadata enrichment.
- `pii_redaction.txt`: bằng chứng email, phone và dữ liệu nhạy cảm đã được che.

## Tracing và prompt versioning

- `langfuse-trace-list.jpg`: danh sách 22 root traces.
- `trace-baseline-v1.jpg`: baseline/v1, trace `c95a53a2271d57ab0535d20f328a0517`.
- `trace-candidate-v2.jpg`: candidate/v2, trace `618ed2879e900a2f648166a885225cd5`.
- `langfuse-rollback-v1.jpg`: trạng thái cuối production rollback về v1.
- `prompt_rollback.json`: production chuyển sang v2 rồi rollback về v1, kèm trace ID.
- `trace_ids.json`: danh sách 10 trace baseline/candidate.

## Dashboard, SLO và alert

- `validate_dashboard.txt` và `validate-dashboard.txt`: validator 6/6 panel.
- `dashboard-runtime.png`: dashboard runtime đủ latency, traffic, errors, cost, tokens và quality.
- `dashboard.html`: dashboard HTML bổ sung render từ `data/logs.jsonl`.
- SLO và alert nằm trong `config/slo.yaml`, `config/alert_rules.yaml` và `docs/alerts.md`.

## Challenge

- `langfuse-waterfall.jpg`: waterfall trace chậm `599082bcff488877d19bb7182a6ade01`.
- `challenge_trace.json` và `trace_waterfall.txt`: metrics, correlation ID, span duration và root cause.
- `incident_metrics.txt` và `incident_logs.txt`: bằng chứng Metrics → Traces → Logs.
