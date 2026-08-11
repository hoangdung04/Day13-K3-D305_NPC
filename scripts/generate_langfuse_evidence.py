from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(override=True)

from fastapi.testclient import TestClient

from app.challenge import load_challenge
from app.main import app
from app.tracing import get_langfuse_client


EVIDENCE_PATH = REPO_ROOT / "submission" / "evidence" / "trace_ids.json"
LABELS = ("baseline", "candidate")


def main() -> None:
    challenge = load_challenge()
    started_at = datetime.now(timezone.utc)
    requests: list[dict[str, object]] = []

    with TestClient(app) as api_client:
        for label in LABELS:
            os.environ["LANGFUSE_PROMPT_LABEL"] = label
            for payload in challenge.queries:
                response = api_client.post("/chat", json=payload)
                response.raise_for_status()
                body = response.json()
                requests.append(
                    {
                        "label": label,
                        "feature": payload["feature"],
                        "session_id": payload["session_id"],
                        "correlation_id": body["correlation_id"],
                        "latency_ms": body["latency_ms"],
                    }
                )
                print(f"[{label}] {body['correlation_id']} {body['latency_ms']}ms")

    langfuse = get_langfuse_client()
    langfuse.flush()

    correlation_ids = {str(item["correlation_id"]) for item in requests}
    matched: dict[str, object] = {}
    deadline = time.monotonic() + 30
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

    evidence: list[dict[str, object]] = []
    for request in requests:
        correlation_id = str(request["correlation_id"])
        trace = matched.get(correlation_id)
        evidence.append(
            {
                **request,
                "trace_id": getattr(trace, "id", None),
                "trace_url_path": getattr(trace, "html_path", None),
                "prompt_name": "day13-chat",
            }
        )

    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    found = sum(1 for item in evidence if item["trace_id"])
    print(f"TRACE_IDS_FOUND={found}/{len(evidence)}")
    print(f"EVIDENCE={EVIDENCE_PATH}")
    if found < len(evidence):
        raise SystemExit("Langfuse did not return every trace before the timeout")


if __name__ == "__main__":
    main()
