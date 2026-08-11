from __future__ import annotations

import argparse
import html
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct / 100
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def load_events(path: Path, minutes: int) -> list[dict]:
    if not path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    result = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
            timestamp = datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00"))
            if timestamp >= cutoff:
                result.append(event)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return result


def metric_cards(events: list[dict], window: int) -> dict[str, dict]:
    requests = [event for event in events if event.get("event") == "request_received"]
    responses = [event for event in events if event.get("event") == "response_sent"]
    failures = [event for event in events if event.get("event") == "request_failed"]
    latencies = [float(event.get("latency_ms", 0)) for event in responses]
    tokens_in = sum(float(event.get("tokens_in", 0)) for event in responses)
    tokens_out = sum(float(event.get("tokens_out", 0)) for event in responses)
    cost = sum(float(event.get("cost_usd", 0)) for event in responses)
    qualities = [float(event.get("quality_score", 0)) for event in responses]
    return {
        "latency": {"value": percentile(latencies, 95), "detail": f"P50 {percentile(latencies, 50):.0f} · P99 {percentile(latencies, 99):.0f}", "suffix": "ms"},
        "traffic": {"value": len(requests) / max(window, 1), "detail": f"{len(requests)} requests / {window}m", "suffix": "req/min"},
        "errors": {"value": len(failures) / max(len(requests), 1) * 100, "detail": f"{len(failures)} failed / {len(requests)} received", "suffix": "%"},
        "cost": {"value": cost, "detail": f"{len(responses)} billable responses", "suffix": "USD"},
        "tokens": {"value": tokens_in + tokens_out, "detail": f"in {tokens_in:.0f} · out {tokens_out:.0f}", "suffix": "tokens"},
        "quality": {"value": mean(qualities) if qualities else 0, "detail": f"mean of {len(qualities)} responses", "suffix": "score"},
    }


def status(value: float, operator: str, threshold: float) -> str:
    return "healthy" if (value <= threshold if operator == "lte" else value >= threshold) else "breach"


def render(config_path: Path, log_path: Path, output_path: Path) -> Path:
    dashboard = yaml.safe_load(config_path.read_text(encoding="utf-8"))["dashboard"]
    window = int(dashboard["time_range_minutes"])
    events = load_events(log_path, window)
    metrics = metric_cards(events, window)
    cards = []
    for panel in dashboard["panels"]:
        item = metrics[panel["id"]]
        threshold = panel["threshold"]
        state = status(float(item["value"]), threshold["operator"], float(threshold["value"]))
        comparator = "≤" if threshold["operator"] == "lte" else "≥"
        value = f"{item['value']:.4f}" if panel["id"] == "cost" else f"{item['value']:.2f}"
        cards.append(f"""
        <section class="panel {state}" data-panel-id="{html.escape(panel['id'])}">
          <div class="panel-head"><span class="eyebrow">{html.escape(panel['id'].upper())}</span><span class="status">{state}</span></div>
          <h2>{html.escape(panel['title'])}</h2>
          <div class="metric">{value} <small>{html.escape(item['suffix'])}</small></div>
          <div class="detail">{html.escape(item['detail'])}</div>
          <div class="threshold">SLO threshold · {html.escape(threshold['aggregation'])} {comparator} {threshold['value']} {html.escape(panel['unit'])}</div>
          <div class="source">data/logs.jsonl · {html.escape(', '.join(panel['aggregations']))}</div>
        </section>""")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="{dashboard['refresh_seconds']}"><title>{html.escape(dashboard['title'])}</title>
<style>
:root{{--bg:#08111f;--card:#101d31;--line:#24344c;--text:#eef5ff;--muted:#92a5bf;--cyan:#52d7e9;--green:#45dfa0;--red:#ff6b7a}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% -10%,#153660 0,transparent 35%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui;padding:34px}}
.wrap{{max-width:1400px;margin:auto}} header{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:26px}} h1{{font-size:32px;margin:6px 0}} .kicker,.meta,.source{{color:var(--muted)}} .kicker{{letter-spacing:.16em;text-transform:uppercase;font-size:12px}} .meta{{text-align:right;line-height:1.7}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}} .panel{{position:relative;background:linear-gradient(145deg,rgba(20,37,61,.96),rgba(12,24,42,.96));border:1px solid var(--line);border-radius:16px;padding:22px;min-height:245px;overflow:hidden}}
.panel:after{{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:var(--green)}} .panel.breach:after{{background:var(--red)}} .panel-head{{display:flex;justify-content:space-between}} .eyebrow{{color:var(--cyan);font-weight:700;font-size:12px;letter-spacing:.15em}} .status{{font-size:11px;text-transform:uppercase;border-radius:99px;padding:5px 9px;background:#173f39;color:var(--green)}} .breach .status{{background:#482331;color:#ff9baa}}
h2{{font-size:17px;margin:18px 0 10px}} .metric{{font-size:38px;font-weight:760;letter-spacing:-.04em}} .metric small{{font-size:14px;color:var(--muted);letter-spacing:0}} .detail{{color:#c3d3e8;margin:8px 0 22px}} .threshold{{font-size:13px;border-top:1px solid var(--line);padding-top:14px;color:#cce8ee}} .source{{font-size:11px;margin-top:9px}}
footer{{margin-top:18px;color:var(--muted);font-size:12px}} @media(max-width:900px){{.grid{{grid-template-columns:1fr}} header{{align-items:flex-start;gap:12px;flex-direction:column}}.meta{{text-align:left}}}}
</style></head><body><main class="wrap"><header><div><div class="kicker">AI Operations · Runtime Dashboard</div><h1>{html.escape(dashboard['title'])}</h1><div class="kicker">Owner · Tran Viet Truong · 2A202601467</div></div><div class="meta">Time range: Last {window} minutes<br>Auto refresh: {dashboard['refresh_seconds']} seconds<br>Generated: {generated}</div></header><div class="grid">{''.join(cards)}</div><footer>{len(events)} log events in active window · thresholds loaded from config/dashboard.yaml</footer></main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render dashboard runtime từ data/logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config/dashboard.yaml")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data/logs.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "submission/evidence/dashboard.html")
    args = parser.parse_args()
    print(render(args.config, args.logs, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
