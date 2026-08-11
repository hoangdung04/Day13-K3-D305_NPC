from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.prompt_management import PROMPT_V1_TEMPLATE, PROMPT_V2_TEMPLATE
from app.tracing import get_langfuse_client, tracing_enabled


def create_versions(client, name: str) -> tuple[int, int]:
    v1 = client.create_prompt(
        name=name,
        prompt=PROMPT_V1_TEMPLATE,
        labels=["baseline", "production"],
        type="text",
        tags=["day13", "2A202601467"],
        commit_message="v1 baseline by Tran Viet Truong (2A202601467)",
    )
    v2 = client.create_prompt(
        name=name,
        prompt=PROMPT_V2_TEMPLATE,
        labels=["candidate"],
        type="text",
        tags=["day13", "2A202601467"],
        commit_message="v2 candidate with concise observable next step",
    )
    client.flush()
    return int(v1.version), int(v2.version)


def move_production(client, name: str, version: int) -> int:
    client.update_prompt(name=name, version=version, new_labels=["production"])
    client.flush()
    return version


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Tạo và rollback prompt Day 13 trên Langfuse")
    parser.add_argument("action", choices=("create", "promote", "rollback", "plan"))
    parser.add_argument("--version", type=int, help="Version đích cho promote/rollback")
    args = parser.parse_args()
    name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")

    if args.action == "plan":
        print(f"Prompt: {name}")
        print("v1 labels: baseline, production")
        print("v2 labels: candidate")
        print("promote: chuyển production sang version 2")
        print("rollback: chuyển production về version 1")
        return 0
    if not tracing_enabled():
        print("Thiếu LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY trong .env; không thay đổi remote.")
        return 2

    client = get_langfuse_client()
    if args.action == "create":
        v1, v2 = create_versions(client, name)
        print(f"Đã tạo {name}: baseline/production=v{v1}, candidate=v{v2}")
        return 0
    target = args.version
    if target is None:
        target = 2 if args.action == "promote" else 1
    selected_version = move_production(client, name, target)
    print(f"Đã {args.action} label production sang {name} v{selected_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
