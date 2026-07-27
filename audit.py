# audit.py
from __future__ import annotations
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    timestamp: float
    actor: str
    event_type: str
    details: dict
    prev_hash: str
    entry_hash: str = field(default="")

    def to_dict(self) -> dict:
        return asdict(self)


def _compute_hash(entry_id: str, timestamp: float, actor: str,
                   event_type: str, details: dict, prev_hash: str) -> str:
    payload = json.dumps(
        {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "actor": actor,
            "event_type": event_type,
            "details": details,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class AuditStore:
    def __init__(self, persist_path: Optional[str] = None):
        self.__entries: list[AuditEntry] = []
        self.__persist_path = persist_path

    def append(self, actor: str, event_type: str, details: dict) -> AuditEntry:
        prev_hash = self.__entries[-1].entry_hash if self.__entries else GENESIS_HASH
        entry_id = str(uuid.uuid4())
        timestamp = time.time()
        entry_hash = _compute_hash(entry_id, timestamp, actor, event_type, details, prev_hash)
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            actor=actor,
            event_type=event_type,
            details=details,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self.__entries.append(entry)
        if self.__persist_path:
            with open(self.__persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        return entry

    def all_entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self.__entries)

    def verify_integrity(self) -> bool:
        prev_hash = GENESIS_HASH
        for entry in self.__entries:
            expected = _compute_hash(
                entry.entry_id, entry.timestamp, entry.actor,
                entry.event_type, entry.details, prev_hash,
            )
            if expected != entry.entry_hash or entry.prev_hash != prev_hash:
                return False
            prev_hash = entry.entry_hash
        return True

    def __len__(self) -> int:
        return len(self.__entries)

