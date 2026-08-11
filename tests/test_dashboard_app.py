from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

import dashboard_app


def _record(event: str, **fields) -> dict:
    return {
        "ts": "2026-08-11T03:30:00Z",
        "event": event,
        **fields,
    }


def test_dashboard_snapshot_has_six_contract_panels() -> None:
    config = dashboard_app.load_dashboard_config()
    records = [
        _record("request_received"),
        _record("request_received"),
        _record("request_failed", error_type="TimeoutError"),
        _record(
            "response_sent",
            latency_ms=250,
            cost_usd=0.01,
            tokens_in=10,
            tokens_out=20,
            quality_score=0.8,
        ),
        _record(
            "response_sent",
            latency_ms=750,
            cost_usd=0.02,
            tokens_in=30,
            tokens_out=40,
            quality_score=0.6,
        ),
    ]

    snapshot = dashboard_app.build_snapshot(records, config)

    assert set(snapshot["panels"]) == {"latency", "traffic", "errors", "cost", "tokens", "quality"}
    assert snapshot["panels"]["latency"]["p95"] == 750
    assert snapshot["panels"]["errors"]["rate"] == 50
    assert snapshot["panels"]["cost"]["total"] == 0.03
    assert snapshot["panels"]["tokens"]["tokens_out"] == 60
    assert snapshot["panels"]["quality"]["mean"] == 0.7


def test_dashboard_ignores_records_outside_window(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    records = [
        _record("request_received"),
        {"ts": "2026-08-11T01:00:00Z", "event": "request_received"},
    ]
    log_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    loaded = dashboard_app.load_records(
        log_path,
        window_minutes=60,
        now=datetime(2026, 8, 11, 3, 45, tzinfo=timezone.utc),
    )

    assert len(loaded) == 1


def test_dashboard_page_renders_all_panels(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        json.dumps(
            _record(
                "response_sent",
                latency_ms=100,
                cost_usd=0.001,
                tokens_in=10,
                tokens_out=20,
                quality_score=0.9,
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_app, "LOG_PATH", log_path)

    response = TestClient(dashboard_app.app).get("/")

    assert response.status_code == 200
    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        assert f'data-panel-id="{panel_id}"' in response.text
    assert "Refresh: 30 seconds" in response.text

