# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: High chat latency
- Severity: warning
- SLI/SLO liên quan: P95 latency <= 3000 ms
- Điều kiện và thời gian duy trì: P95 > 3000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời chậm, tăng nguy cơ timeout.
- Ba bước kiểm tra đầu tiên: (1) xác nhận time range và traffic; (2) mở trace chậm nhất, so span retrieval/generation; (3) tìm log theo correlation ID để kiểm tra incident/error.
- Mitigation tạm thời: giảm concurrency hoặc tắt incident, sau đó rollback prompt nếu generation tăng bất thường.
- Owner: Trần Việt Trường (2A202601467)

## Alert 2

- Tên: Elevated request error rate
- Severity: critical
- SLI/SLO liên quan: error rate <= 2%
- Điều kiện và thời gian duy trì: error rate > 2% trong 5 phút và có ít nhất 20 request.
- Ảnh hưởng tới người dùng: request `/chat` thất bại hoặc không có câu trả lời.
- Ba bước kiểm tra đầu tiên: (1) kiểm tra traffic để loại mẫu quá nhỏ; (2) breakdown `error_type`; (3) mở trace lỗi và log cùng correlation ID.
- Mitigation tạm thời: rollback thay đổi gần nhất hoặc chuyển về prompt baseline/production ổn định.
- Owner: Trần Việt Trường (2A202601467)

## Alert 3

- Tên: Quality proxy degradation
- Severity: warning
- SLI/SLO liên quan: quality score trung bình >= 0.75
- Điều kiện và thời gian duy trì: mean < 0.75 trong 15 phút và có ít nhất 20 response.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu tài liệu, quá ngắn hoặc chứa dấu hiệu redaction.
- Ba bước kiểm tra đầu tiên: (1) phân nhóm theo feature/model/prompt version; (2) so trace baseline và candidate cùng input; (3) kiểm tra retrieval docs và generation metadata.
- Mitigation tạm thời: chuyển label `production` về prompt version baseline đã xác nhận.
- Owner: Trần Việt Trường (2A202601467)
