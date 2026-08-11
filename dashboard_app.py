from __future__ import annotations

import html
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"

app = FastAPI(title="Day 13 AI Observability Dashboard")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_dashboard_config(path: Path = DASHBOARD_CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["dashboard"]


def load_records(
    path: Path | None = None,
    *,
    window_minutes: int = 60,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    source_path = path or LOG_PATH
    if not source_path.exists():
        return []

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current_time - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and timestamp >= cutoff:
            records.append(record)
    return records


def percentile(values: list[float], value: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((value / 100) * len(ordered)) - 1))
    return float(ordered[index])


def _minute_series(records: list[dict[str, Any]], field: str | None = None) -> list[dict[str, Any]]:
    buckets: defaultdict[str, float] = defaultdict(float)
    for record in records:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is None:
            continue
        minute = timestamp.strftime("%H:%M")
        buckets[minute] += float(record.get(field, 0) or 0) if field else 1.0
    return [{"minute": minute, "value": round(buckets[minute], 6)} for minute in sorted(buckets)]


def _thresholds(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {panel["id"]: panel["threshold"] for panel in config["panels"]}


def build_snapshot(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    requests = [record for record in records if record.get("event") == "request_received"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    responses = [record for record in records if record.get("event") == "response_sent"]

    latencies = [float(record.get("latency_ms", 0) or 0) for record in responses]
    quality_values = [float(record.get("quality_score", 0) or 0) for record in responses]
    error_rate = (len(failures) / len(requests) * 100) if requests else 0.0
    error_breakdown = Counter(str(record.get("error_type") or "Unknown") for record in failures)
    traffic_series = _minute_series(requests)
    cost_series = _minute_series(responses, "cost_usd")
    thresholds = _thresholds(config)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "time_range_minutes": config["time_range_minutes"],
        "refresh_seconds": config["refresh_seconds"],
        "record_count": len(records),
        "panels": {
            "latency": {
                "p50": round(percentile(latencies, 50), 2),
                "p95": round(percentile(latencies, 95), 2),
                "p99": round(percentile(latencies, 99), 2),
                "unit": "ms",
                "threshold": thresholds["latency"],
            },
            "traffic": {
                "total": len(requests),
                "latest_rate": traffic_series[-1]["value"] if traffic_series else 0,
                "series": traffic_series,
                "unit": "requests_per_minute",
                "threshold": thresholds["traffic"],
            },
            "errors": {
                "rate": round(error_rate, 2),
                "total": len(failures),
                "breakdown": dict(error_breakdown),
                "unit": "percent",
                "threshold": thresholds["errors"],
            },
            "cost": {
                "total": round(sum(float(record.get("cost_usd", 0) or 0) for record in responses), 6),
                "series": cost_series,
                "unit": "usd",
                "threshold": thresholds["cost"],
            },
            "tokens": {
                "tokens_in": sum(int(record.get("tokens_in", 0) or 0) for record in responses),
                "tokens_out": sum(int(record.get("tokens_out", 0) or 0) for record in responses),
                "unit": "tokens",
                "threshold": thresholds["tokens"],
            },
            "quality": {
                "mean": round(mean(quality_values), 3) if quality_values else 0.0,
                "unit": "score_0_to_1",
                "threshold": thresholds["quality"],
            },
        },
    }


def _status(value: float, threshold: dict[str, Any]) -> tuple[str, str]:
    target = float(threshold["value"])
    healthy = value <= target if threshold["operator"] == "lte" else value >= target
    return ("healthy", "Within threshold") if healthy else ("breach", "Threshold breached")


def _sparkline(values: list[float], label: str) -> str:
    clean_values = values or [0.0]
    width, height, padding = 360, 90, 10
    low, high = min(clean_values), max(clean_values)
    spread = high - low or 1.0
    points: list[str] = []
    for index, value in enumerate(clean_values):
        x = padding + (index / max(1, len(clean_values) - 1)) * (width - 2 * padding)
        y = height - padding - ((value - low) / spread) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")
    escaped_label = html.escape(label)
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escaped_label}">'
        f"<title>{escaped_label}</title>"
        '<line x1="10" y1="80" x2="350" y2="80" class="axis" />'
        f'<polyline points="{" ".join(points)}" class="series" />'
        "</svg>"
    )


def render_dashboard(snapshot: dict[str, Any]) -> str:
    panels = snapshot["panels"]
    latency = panels["latency"]
    traffic = panels["traffic"]
    errors = panels["errors"]
    cost = panels["cost"]
    tokens = panels["tokens"]
    quality = panels["quality"]

    latency_state, latency_text = _status(latency["p95"], latency["threshold"])
    traffic_state, traffic_text = _status(traffic["latest_rate"], traffic["threshold"])
    error_state, error_text = _status(errors["rate"], errors["threshold"])
    cost_state, cost_text = _status(cost["total"], cost["threshold"])
    token_state, token_text = _status(max(tokens["tokens_in"], tokens["tokens_out"]), tokens["threshold"])
    quality_state, quality_text = _status(quality["mean"], quality["threshold"])
    traffic_values = [float(item["value"]) for item in traffic["series"]]
    cost_values = [float(item["value"]) for item in cost["series"]]
    error_breakdown = ", ".join(f"{html.escape(name)}: {count}" for name, count in errors["breakdown"].items()) or "No errors"

    refresh = int(snapshot["refresh_seconds"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{refresh}">
  <title>Day 13 AI Observability Dashboard</title>
  <style>
    :root {{ color-scheme: light dark; --bg:#f4f6f8; --panel:#ffffff; --text:#17202a; --muted:#5f6b76; --border:#d7dde3; --good:#15803d; --bad:#b91c1c; --series:#2563eb; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1419; --panel:#182027; --text:#eef2f6; --muted:#aab4be; --border:#34404b; --good:#4ade80; --bad:#fb7185; --series:#60a5fa; }} }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:ui-sans-serif,system-ui,sans-serif; }}
    main {{ width:min(1180px, calc(100% - 32px)); margin:24px auto 48px; }}
    header {{ display:flex; justify-content:space-between; gap:20px; align-items:end; margin-bottom:18px; flex-wrap:wrap; }}
    h1 {{ margin:0 0 6px; font-size:1.65rem; }}
    h2 {{ margin:0; font-size:1rem; }}
    p {{ margin:0; }}
    .meta {{ color:var(--muted); font-size:.88rem; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:18px; min-width:0; }}
    .panel-head {{ display:flex; justify-content:space-between; gap:12px; align-items:start; }}
    .value {{ font-size:2rem; font-weight:700; margin:12px 0 2px; font-variant-numeric:tabular-nums; }}
    .unit,.detail {{ color:var(--muted); font-size:.85rem; }}
    .status {{ margin-top:10px; font-size:.84rem; font-weight:600; }}
    .healthy {{ color:var(--good); }} .breach {{ color:var(--bad); }}
    .chart {{ width:100%; height:90px; margin-top:12px; overflow:visible; }}
    .axis {{ stroke:var(--border); stroke-width:1; }}
    .series {{ fill:none; stroke:var(--series); stroke-width:3; stroke-linejoin:round; stroke-linecap:round; }}
    dl {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:14px 0 0; }}
    dt {{ color:var(--muted); font-size:.78rem; }} dd {{ margin:2px 0 0; font-weight:700; }}
    @media (max-width:720px) {{ .grid {{ grid-template-columns:1fr; }} main {{ width:min(100% - 20px,1180px); margin-top:14px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div><h1>Day 13 AI Observability</h1><p class="meta">Source: data/logs.jsonl · Window: {snapshot['time_range_minutes']} minutes · Refresh: {refresh} seconds</p></div>
    <p class="meta">Records in window: {snapshot['record_count']}</p>
  </header>
  <div class="grid">
    <section class="panel" data-panel-id="latency"><div class="panel-head"><h2>Latency percentiles</h2><span class="unit">ms</span></div><div class="value">{latency['p95']:.0f} ms</div><p class="detail">P95 · threshold ≤ {latency['threshold']['value']} ms</p><dl><div><dt>P50</dt><dd>{latency['p50']:.0f}</dd></div><div><dt>P95</dt><dd>{latency['p95']:.0f}</dd></div><div><dt>P99</dt><dd>{latency['p99']:.0f}</dd></div></dl>{_sparkline([latency['p50'], latency['p95'], latency['p99']], 'Latency P50 P95 P99')}<p class="status {latency_state}">{latency_text}</p></section>
    <section class="panel" data-panel-id="traffic"><div class="panel-head"><h2>Request traffic</h2><span class="unit">requests/min</span></div><div class="value">{traffic['latest_rate']:.0f}</div><p class="detail">Latest minute · total {traffic['total']} requests</p>{_sparkline(traffic_values, 'Request traffic per minute')}<p class="status {traffic_state}">{traffic_text}</p></section>
    <section class="panel" data-panel-id="errors"><div class="panel-head"><h2>Error rate and breakdown</h2><span class="unit">%</span></div><div class="value">{errors['rate']:.2f}%</div><p class="detail">Threshold ≤ {errors['threshold']['value']}% · {error_breakdown}</p>{_sparkline([errors['rate']], 'Error rate')}<p class="status {error_state}">{error_text}</p></section>
    <section class="panel" data-panel-id="cost"><div class="panel-head"><h2>Cost over time</h2><span class="unit">USD</span></div><div class="value">${cost['total']:.4f}</div><p class="detail">60-minute total · threshold ≤ ${cost['threshold']['value']}</p>{_sparkline(cost_values, 'Cost by minute')}<p class="status {cost_state}">{cost_text}</p></section>
    <section class="panel" data-panel-id="tokens"><div class="panel-head"><h2>Input and output tokens</h2><span class="unit">tokens</span></div><div class="value">{tokens['tokens_in'] + tokens['tokens_out']}</div><p class="detail">Input {tokens['tokens_in']} · Output {tokens['tokens_out']} · threshold ≤ {tokens['threshold']['value']}</p>{_sparkline([tokens['tokens_in'], tokens['tokens_out']], 'Input and output token totals')}<p class="status {token_state}">{token_text}</p></section>
    <section class="panel" data-panel-id="quality"><div class="panel-head"><h2>Quality proxy</h2><span class="unit">score 0–1</span></div><div class="value">{quality['mean']:.3f}</div><p class="detail">Mean quality · threshold ≥ {quality['threshold']['value']}</p>{_sparkline([quality['mean']], 'Mean quality score')}<p class="status {quality_state}">{quality_text}</p></section>
  </div>
</main>
</body>
</html>"""


def current_snapshot() -> dict[str, Any]:
    config = load_dashboard_config()
    records = load_records(window_minutes=int(config["time_range_minutes"]))
    return build_snapshot(records, config)


@app.get("/api/dashboard")
def dashboard_data() -> dict[str, Any]:
    return current_snapshot()


@app.get("/", response_class=HTMLResponse)
def dashboard_page() -> HTMLResponse:
    return HTMLResponse(render_dashboard(current_snapshot()))
