from __future__ import annotations

from types import SimpleNamespace

from scripts.manage_prompts import create_versions, move_production


class RecordingClient:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.updated: list[dict] = []
        self.flush_count = 0

    def create_prompt(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(version=len(self.created))

    def update_prompt(self, **kwargs):
        self.updated.append(kwargs)

    def flush(self) -> None:
        self.flush_count += 1


def test_create_versions_assigns_required_labels() -> None:
    client = RecordingClient()
    assert create_versions(client, "day13-chat") == (1, 2)
    assert client.created[0]["labels"] == ["baseline", "production"]
    assert client.created[1]["labels"] == ["candidate"]
    assert client.created[0]["prompt"] != client.created[1]["prompt"]


def test_move_production_updates_existing_version_without_new_revision() -> None:
    client = RecordingClient()
    assert move_production(client, "day13-chat", 2) == 2
    assert client.updated == [
        {"name": "day13-chat", "version": 2, "new_labels": ["production"]}
    ]
    assert client.created == []
