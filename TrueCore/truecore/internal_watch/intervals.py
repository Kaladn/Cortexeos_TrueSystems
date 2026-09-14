"""Independent time-bounded observation records. No work-job dependency."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from truecore.receipt_store import atomic_json, digest, read_json, record_lock


def _seconds(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def publish_observation(root, receipt, *, interval_seconds=60):
    if not 1 <= interval_seconds <= 3600:
        raise ValueError("invalid observation interval")
    root = Path(root)
    key = digest([receipt["kind"], receipt["host_id"], receipt["observer_id"]])
    index = root / (key + ".current.json")
    with record_lock(root / (key + ".lock")):
        state = {k: v for k, v in receipt.items() if k not in {"created_at_utc", "receipt_id"}}
        state_hash = digest(state)
        now = _seconds(receipt["created_at_utc"])
        previous = None
        if index.exists():
            pointer = read_json(index)
            name = pointer["name"]
            if Path(name).name != name:
                raise ValueError("invalid observation reference")
            previous = read_json(root / name)
        old = (previous or {}).get("observation_interval", {})
        same = (old.get("state_sha256") == state_hash
                and 0 <= now - _seconds(old["first_observed_at_utc"]) < interval_seconds
                and now >= _seconds(old["last_observed_at_utc"]))
        if same:
            name = pointer["name"]
            count = old["observation_count"] + 1
            first = old["first_observed_at_utc"]
        else:
            name = f"{key[:16]}-{uuid4().hex}.observation.json"
            count, first = 1, receipt["created_at_utc"]
        receipt["observation_interval"] = {
            "schema": "truecore.independent_observation_interval@1",
            "first_observed_at_utc": first,
            "last_observed_at_utc": receipt["created_at_utc"],
            "observation_count": count, "state_sha256": state_hash,
            "interval_seconds": interval_seconds,
            "same_state_samples_coalesced": count - 1,
            "continuous_monitoring_proven": False,
        }
        path = root / name
        atomic_json(path, receipt)
        atomic_json(index, {"name": name})
    receipt["receipt_path"] = str(path)
    return receipt


def read_observation(path, *, now_utc=None, max_age_seconds=60):
    """Freshness is assessed on read; an old green record is never current proof."""
    if not 0 < max_age_seconds <= 3600:
        raise ValueError("invalid freshness limit")
    receipt = read_json(path)
    now = datetime.now(timezone.utc).timestamp() if now_utc is None else _seconds(now_utc)
    age = now - _seconds(receipt["created_at_utc"])
    return {"receipt": receipt, "fresh": 0 <= age <= max_age_seconds,
            "effective_status": receipt["status"] if 0 <= age <= max_age_seconds else "unknown_stale",
            "age_seconds": age}
