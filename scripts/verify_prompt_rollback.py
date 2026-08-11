from __future__ import annotations

import argparse
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


EVIDENCE_PATH = REPO_ROOT / "submission" / "evidence" / "prompt_rollback.json"
LABELS_BY_VERSION = {
    1: ["baseline", "production"],
    2: ["candidate", "production"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, choices=(1, 2), required=True)
    parser.add_argument("--phase", required=True)
    args = parser.parse_args()

    langfuse = get_langfuse_client()
    labels = LABELS_BY_VERSION[args.version]
    langfuse.update_prompt(
        name="day13-chat",
        version=args.version,
        new_labels=labels,
    )
    print(f"PRODUCTION_VERSION={args.version} LABELS={labels}")

    os.environ["LANGFUSE_PROMPT_LABEL"] = "production"
    query = load_challenge().queries[0]
    started_at = datetime.now(timezone.utc)
    with TestClient(app) as api_client:
        response = api_client.post("/chat", json=query)
        response.raise_for_status()
        body = response.json()

    langfuse.flush()
    correlation_id = body["correlation_id"]
    trace = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and trace is None:
        traces = langfuse.api.trace.list(
            from_timestamp=started_at - timedelta(minutes=1),
            limit=50,
            order_by="timestamp.desc",
        )
        for candidate in traces.data:
            metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
            if metadata.get("correlation_id") == correlation_id:
                trace = candidate
                break
        if trace is None:
            time.sleep(2)

    if trace is None:
        raise SystemExit("Trace was not returned before the timeout")

    metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
    evidence = []
    if EVIDENCE_PATH.exists():
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence = [item for item in evidence if item.get("phase") != args.phase]
    evidence.append(
        {
            "phase": args.phase,
            "production_version": args.version,
            "labels": labels,
            "trace_id": trace.id,
            "trace_url_path": trace.html_path,
            "correlation_id": correlation_id,
            "prompt_name": metadata.get("prompt_name"),
            "prompt_label": metadata.get("prompt_label"),
            "prompt_version": metadata.get("prompt_version"),
        }
    )
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"TRACE_ID={trace.id}")
    print(f"CORRELATION_ID={correlation_id}")
    print(f"PROMPT_VERSION={metadata.get('prompt_version')}")


if __name__ == "__main__":
    main()
