# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighP95Latency
- Severity: critical
- SLI/SLO liên quan: `latency_p95_ms`, objective ≤ 3000 ms và target 99.5% trong 28 ngày.
- Điều kiện và thời gian duy trì: P95 latency > 3000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: Câu trả lời AI chậm, request có thể timeout và làm giảm khả năng hoàn thành tác vụ.
- Ba bước kiểm tra đầu tiên: (1) xác nhận time range, traffic và panel P95; (2) mở trace chậm nhất và so thời gian retrieval/generation; (3) dùng correlation ID để đối chiếu log, feature và model.
- Mitigation tạm thời: Bật fallback/cache cho retrieval hoặc model, giảm concurrency tới dependency đang chậm và rollback thay đổi gần nhất nếu có tương quan thời gian.
- Owner: Trần Việt Trường (2A202601467)

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- SLI/SLO liên quan: `error_rate_pct`, objective ≤ 2% và target 99.0% trong 28 ngày.
- Điều kiện và thời gian duy trì: Error rate > 2% liên tục 5 phút, với ít nhất 20 request để tránh cảnh báo do mẫu quá nhỏ.
- Ảnh hưởng tới người dùng: Request `/chat` thất bại hoặc không nhận được câu trả lời hợp lệ.
- Ba bước kiểm tra đầu tiên: (1) kiểm tra traffic và breakdown theo `error_type`; (2) mở trace của lỗi phổ biến nhất; (3) tìm log `request_failed` cùng correlation ID và kiểm tra dependency liên quan.
- Mitigation tạm thời: Cô lập dependency lỗi, bật fallback/retry có giới hạn và rollback release gây tăng lỗi.
- Owner: Trần Việt Trường (2A202601467)

## Alert 3

- Tên: LowQualityScore
- Severity: warning
- SLI/SLO liên quan: `quality_score_avg`, objective ≥ 0.75 và target 95.0% trong 28 ngày.
- Điều kiện và thời gian duy trì: Quality score trung bình < 0.75 liên tục 15 phút, với ít nhất 20 response.
- Ảnh hưởng tới người dùng: Hệ thống vẫn trả lời nhưng nội dung có thể thiếu căn cứ, không liên quan hoặc không đủ hữu ích.
- Ba bước kiểm tra đầu tiên: (1) phân nhóm quality theo feature/model/prompt version; (2) so trace baseline và candidate cùng input; (3) kiểm tra retrieval docs và output generation của các trace điểm thấp.
- Mitigation tạm thời: Rollback label `production` về prompt baseline đã kiểm chứng và chuyển sang fallback khi retrieval không có tài liệu phù hợp.
- Owner: Trần Việt Trường (2A202601467)
