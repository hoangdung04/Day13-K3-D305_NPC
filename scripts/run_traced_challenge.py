from __future__ import annotations

import concurrent.futures
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(override=True)

from app.challenge import load_challenge
from app.tracing import get_langfuse_client


BASE_URL = "http://127.0.0.1:8013"
EVIDENCE_PATH = REPO_ROOT / "submission" / "evidence" / "challenge_trace.json"


def send_request(payload: dict[str, str]) -> dict[str, object]:
    started = time.perf_counter()
    response = httpx.post(f"{BASE_URL}/chat", json=payload, timeout=30.0)
    response.raise_for_status()
    body = response.json()
    return {
        "correlation_id": body["correlation_id"],
        "latency_ms": body["latency_ms"],
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        "session_id": payload["session_id"],
        "feature": payload["feature"],
    }


def send_batch(queries: tuple[dict[str, str], ...]) -> list[dict[str, object]]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(send_request, queries))


def wait_for_server() -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Challenge server did not start")


def trace_map(correlation_ids: set[str], started_at: datetime) -> dict[str, object]:
    langfuse = get_langfuse_client()
    matched: dict[str, object] = {}
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline and len(matched) < len(correlation_ids):
        traces = langfuse.api.trace.list(
            from_timestamp=started_at - timedelta(minutes=1),
            limit=100,
            order_by="timestamp.desc",
        )
        for trace in traces.data:
            metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
            correlation_id = metadata.get("correlation_id")
            if correlation_id in correlation_ids:
                matched[str(correlation_id)] = trace
        if len(matched) < len(correlation_ids):
            time.sleep(2)
    return matched


def observation_summary(trace_id: str) -> list[dict[str, object]]:
    observations = get_langfuse_client().api.observations.get_many(
        trace_id=trace_id,
        limit=100,
    )
    result: list[dict[str, object]] = []
    for observation in observations.data:
        start = getattr(observation, "start_time", None)
        end = getattr(observation, "end_time", None)
        duration_ms = None
        if start is not None and end is not None:
            duration_ms = round((end - start).total_seconds() * 1000, 1)
        result.append(
            {
                "id": getattr(observation, "id", None),
                "name": getattr(observation, "name", None),
                "type": getattr(observation, "type", None),
                "parent_observation_id": getattr(observation, "parent_observation_id", None),
                "duration_ms": duration_ms,
            }
        )
    return result


def main() -> None:
    challenge = load_challenge()
    started_at = datetime.now(timezone.utc)
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8013",
            "--env-file",
            ".env",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )

    try:
        wait_for_server()
        baseline = send_batch(challenge.queries)
        baseline_metrics = httpx.get(f"{BASE_URL}/metrics", timeout=5.0).json()

        enable = httpx.post(f"{BASE_URL}/incidents/{challenge.incident}/enable", timeout=5.0)
        enable.raise_for_status()
        incident = send_batch(challenge.queries)
        incident_metrics = httpx.get(f"{BASE_URL}/metrics", timeout=5.0).json()

        disable = httpx.post(f"{BASE_URL}/incidents/{challenge.incident}/disable", timeout=5.0)
        disable.raise_for_status()
        time.sleep(6)

        correlation_ids = {
            str(item["correlation_id"])
            for item in [*baseline, *incident]
        }
        traces = trace_map(correlation_ids, started_at)
        for item in [*baseline, *incident]:
            trace = traces.get(str(item["correlation_id"]))
            item["trace_id"] = getattr(trace, "id", None)
            item["trace_url_path"] = getattr(trace, "html_path", None)

        slowest = max(incident, key=lambda item: float(item["latency_ms"]))
        if not slowest.get("trace_id"):
            raise RuntimeError("Slow incident trace was not returned by Langfuse")

        evidence = {
            "challenge_id": challenge.challenge_id,
            "scenario": challenge.incident,
            "affected_feature": challenge.affected_feature,
            "latency_threshold_ms": challenge.latency_threshold_ms,
            "baseline_metrics": baseline_metrics,
            "incident_metrics": incident_metrics,
            "baseline_requests": baseline,
            "incident_requests": incident,
            "slowest_incident": slowest,
            "waterfall": observation_summary(str(slowest["trace_id"])),
            "root_cause": "rag_retrieval blocks for 2.5 seconds while rag_slow is enabled",
        }
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"BASELINE_P95={baseline_metrics['latency_p95']}")
        print(f"INCIDENT_P95={incident_metrics['latency_p95']}")
        print(f"SLOW_TRACE_ID={slowest['trace_id']}")
        print(f"SLOW_CORRELATION_ID={slowest['correlation_id']}")
        for observation in evidence["waterfall"]:
            print(f"SPAN={observation['name']} DURATION_MS={observation['duration_ms']}")
        print(f"EVIDENCE={EVIDENCE_PATH}")
    finally:
        try:
            httpx.post(f"{BASE_URL}/incidents/{challenge.incident}/disable", timeout=2.0)
        except httpx.HTTPError:
            pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
