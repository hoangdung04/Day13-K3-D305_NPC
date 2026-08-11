from __future__ import annotations

import json
from datetime import datetime, timezone

from scripts.render_dashboard import percentile, render


def test_percentile_interpolates() -> None:
    assert percentile([10, 20, 30], 50) == 20
    assert percentile([], 95) == 0


def test_runtime_dashboard_renders_six_panels(tmp_path) -> None:
    logs = tmp_path / "logs.jsonl"
    logs.write_text(
        "\n".join(
            json.dumps(event)
            for event in (
                {"ts": datetime.now(timezone.utc).isoformat(), "event": "request_received"},
                {"ts": datetime.now(timezone.utc).isoformat(), "event": "response_sent", "latency_ms": 120, "tokens_in": 10, "tokens_out": 20, "cost_usd": 0.001, "quality_score": 0.8},
            )
        ),
        encoding="utf-8",
    )
    output = tmp_path / "dashboard.html"
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    render(repo_root / "config/dashboard.yaml", logs, output)
    page = output.read_text(encoding="utf-8")
    assert page.count('data-panel-id="') == 6
    assert "Time range: Last 60 minutes" in page
    assert "SLO threshold" in page
