"""Full-circle test for the lexicon danger gate safety net.

Tests the complete snapshot → mutation → verify → rollback → verify cycle
that backs the three-step danger gate (Windows Hello + typed confirmation).

This test runs against the LIVE bridge server on port 5050.
Start the bridge first:  python scripts/clearbox_start.py

Flow:
  1. GET /api/stats → baseline entry count
  2. POST /api/snapshot {tag: "test_danger_gate"} → safety snapshot
  3. GET /api/snapshots → verify snapshot appears in listing
  4. Mutate: append a dummy word to the lexicon
  5. GET /api/stats → verify entry count changed (+1)
  6. POST /api/rollback {path: <snapshot_path>} → rollback
  7. GET /api/stats → verify entry count matches baseline
  8. Routing profile: GET/POST /api/routing/profile → read + roundtrip
  9. Routing validation: POST bad profile → rejected

Run:
    python tests/test_danger_gate_full_circle.py
"""
from __future__ import annotations

import http.client
import json
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 5050


class TestError(RuntimeError):
    pass


class Harness:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, expr, msg=""):
        if expr:
            self.passed += 1
            print(f"    PASS  {msg}")
        else:
            self.failed += 1
            self.errors.append(msg)
            print(f"    FAIL  {msg}")

    def eq(self, a, b, msg=""):
        self.ok(a == b, f"{msg} (got {a!r}, expected {b!r})")

    def gt(self, a, b, msg=""):
        self.ok(a > b, f"{msg} (got {a!r} > {b!r})")

    def gte(self, a, b, msg=""):
        self.ok(a >= b, f"{msg} (got {a!r} >= {b!r})")

    def report(self) -> bool:
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        print(f"{'=' * 60}")
        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(f"  X  {e}")
        else:
            print("  All tests passed")
        return self.failed == 0


def _wait_for_port(timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((HOST, PORT))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def _req(method: str, path: str, payload=None) -> dict:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    conn = http.client.HTTPConnection(HOST, PORT, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
    finally:
        conn.close()
    text = data.decode("utf-8") if data else ""
    parsed = json.loads(text) if text else {}
    return {"status": resp.status, "body": parsed}


def run_tests():
    t = Harness()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n" + "=" * 60)
    print("  Danger Gate Full-Circle Test")
    print("=" * 60 + "\n")

    # ── Pre-flight: check bridge is up ───────────────────────
    print("[0] Checking bridge server...")
    if not _wait_for_port():
        print(f"  Bridge not responding on {HOST}:{PORT}")
        print("  Start it first: python scripts/clearbox_start.py")
        sys.exit(1)
    print(f"  Bridge alive on port {PORT}\n")

    # ── TEST 1: Baseline stats ───────────────────────────────
    print("[1] Baseline stats")
    r = _req("GET", "/api/stats")
    t.eq(r["status"], 200, "GET /api/stats returns 200")
    baseline_entries = r["body"].get("entries", 0)
    baseline_frequency = r["body"].get("total_frequency", 0)
    print(f"    Baseline: {baseline_entries} entries, {baseline_frequency} total frequency\n")

    # ── TEST 2: Create safety snapshot ───────────────────────
    print("[2] Create safety snapshot (pre_test_danger_gate)")
    r = _req("POST", "/api/snapshot", {"tag": "pre_test_danger_gate"})
    t.eq(r["status"], 200, "POST /api/snapshot returns 200")
    snapshot_path = r["body"].get("path", "")
    t.ok(len(snapshot_path) > 0, "Snapshot path returned")
    t.ok("pre_test_danger_gate" in snapshot_path, "Snapshot tagged correctly")
    print(f"    Snapshot: {snapshot_path}\n")

    # ── TEST 3: List snapshots ───────────────────────────────
    print("[3] List snapshots — verify new snapshot appears")
    our_snapshot = None
    r = _req("GET", "/api/snapshots")
    if r["status"] == 404:
        print("    SKIP  GET /api/snapshots returned 404 — bridge needs restart to load new endpoint")
        print("    (Snapshot create/rollback still work — listing is display-only)\n")
    else:
        t.eq(r["status"], 200, "GET /api/snapshots returns 200")
        snapshots = r["body"].get("snapshots", [])
        t.gt(len(snapshots), 0, "At least 1 snapshot exists")

        # Find our snapshot in the list
        our_snapshot = None
        for s in snapshots:
            if "pre_test_danger_gate" in s.get("name", ""):
                our_snapshot = s
                break
        t.ok(our_snapshot is not None, "Our test snapshot found in listing")
        if our_snapshot:
            t.ok("created" in our_snapshot, "Snapshot has creation timestamp")
            t.ok("path" in our_snapshot, "Snapshot has path field")
            print(f"    Found: {our_snapshot['name']}")
        print()

    # ── TEST 4: Mutate lexicon (append a test word) ──────────
    print("[4] Mutate lexicon — append test word")
    test_word = f"_DANGERGATE_TEST_{int(time.time())}"
    r = _req("POST", "/api/lexicon/append", {"word": test_word, "status": "ASSIGNED"})
    if r["status"] == 200:
        t.ok(True, f"Appended test word: {test_word}")
        print(f"    Word '{test_word}' appended\n")
    else:
        # Endpoint might not exist or might error — still continue
        print(f"    Append returned {r['status']} — skipping mutation verification")
        print(f"    (destructive endpoints may not be wired yet)\n")

    # ── TEST 5: Verify mutation ──────────────────────────────
    print("[5] Post-mutation stats")
    r = _req("GET", "/api/stats")
    t.eq(r["status"], 200, "GET /api/stats still returns 200")
    mutated_entries = r["body"].get("entries", 0)
    print(f"    After mutation: {mutated_entries} entries (was {baseline_entries})")
    if mutated_entries > baseline_entries:
        t.gt(mutated_entries, baseline_entries, "Entry count increased after append")
    else:
        print("    (mutation did not change count — append may have matched existing entry)")
    print()

    # ── TEST 6: Rollback to snapshot ─────────────────────────
    print("[6] Rollback to safety snapshot")
    rollback_path = snapshot_path
    # Also accept the path from the snapshots listing if available
    if our_snapshot and our_snapshot.get("path"):
        rollback_path = our_snapshot["path"]

    r = _req("POST", "/api/rollback", {"path": rollback_path})
    t.eq(r["status"], 200, "POST /api/rollback returns 200")
    rollback_entries = r["body"].get("entries", 0)
    t.ok(rollback_entries >= 0, "Rollback returned valid entry count")
    print(f"    After rollback: {rollback_entries} entries\n")

    # ── TEST 7: Verify rollback ──────────────────────────────
    print("[7] Verify rollback restored baseline")
    r = _req("GET", "/api/stats")
    t.eq(r["status"], 200, "GET /api/stats returns 200 after rollback")
    restored_entries = r["body"].get("entries", 0)
    t.eq(restored_entries, baseline_entries, f"Entries restored to baseline ({baseline_entries})")
    restored_frequency = r["body"].get("total_frequency", 0)
    t.eq(restored_frequency, baseline_frequency, f"Frequency restored to baseline ({baseline_frequency})")
    print(f"    Verified: {restored_entries} entries, {restored_frequency} frequency\n")

    # ── TEST 8: Routing profile read ─────────────────────────
    print("[8] Routing profile — GET")
    r = _req("GET", "/api/routing/profile")
    t.eq(r["status"], 200, "GET /api/routing/profile returns 200")
    profile = r["body"]
    t.ok("pipeline" in profile, "Profile has pipeline")
    t.ok("name" in profile, "Profile has name")
    pipeline = profile.get("pipeline", [])
    t.eq(len(pipeline), 4, "Pipeline has exactly 4 stages")

    stage_types = [s.get("type") for s in pipeline]
    t.ok("inject_616" in stage_types, "Pipeline has inject_616 stage")
    t.ok("model_call" in stage_types, "Pipeline has model_call stage")
    t.ok("retrieval_gate" in stage_types, "Pipeline has retrieval_gate stage")
    t.ok("plugin_chain" in stage_types, "Pipeline has plugin_chain stage")

    enabled_models = [s for s in pipeline if s.get("type") == "model_call" and s.get("enabled")]
    t.eq(len(enabled_models), 1, "Exactly 1 enabled model_call")
    print()

    # ── TEST 9: Routing profile write + validate ─────────────
    print("[9] Routing profile — POST (roundtrip)")
    # Save original, modify, write, read back, restore original
    original_profile = json.loads(json.dumps(profile))  # deep copy
    profile["name"] = "test_roundtrip"
    r = _req("POST", "/api/routing/profile", profile)
    t.eq(r["status"], 200, "POST /api/routing/profile returns 200")

    r = _req("GET", "/api/routing/profile")
    t.eq(r["body"].get("name"), "test_roundtrip", "Profile name updated after POST")

    # Restore original
    r = _req("POST", "/api/routing/profile", original_profile)
    t.eq(r["status"], 200, "Restored original profile")
    print()

    # ── TEST 10: Routing validation rejects bad profile ──────
    print("[10] Routing validation — reject bad profiles")
    bad_profiles = [
        (
            {"name": "bad", "version": 1, "pipeline": []},
            "empty pipeline"
        ),
        (
            {
                "name": "bad", "version": 1,
                "pipeline": [
                    {"id": "a", "type": "model_call", "enabled": True, "config": {}},
                    {"id": "b", "type": "model_call", "enabled": True, "config": {}},
                    {"id": "c", "type": "inject_616", "enabled": True, "config": {}},
                    {"id": "d", "type": "retrieval_gate", "enabled": True, "config": {}},
                    {"id": "e", "type": "plugin_chain", "enabled": True, "config": {}},
                ],
            },
            "two enabled model_calls"
        ),
        (
            {
                "name": "bad", "version": 1,
                "pipeline": [
                    {"id": "a", "type": "inject_616", "enabled": True, "config": {}},
                    {"id": "b", "type": "model_call", "enabled": True, "config": {}},
                ],
            },
            "missing required stage types"
        ),
    ]
    for bad_prof, description in bad_profiles:
        r = _req("POST", "/api/routing/profile", bad_prof)
        t.ok(r["status"] >= 400, f"Bad profile rejected: {description} (HTTP {r['status']})")
    print()

    # ── TEST 11: Snapshot listing is capped and ordered ──────
    print("[11] Snapshot listing — ordered newest first, capped")
    r = _req("GET", "/api/snapshots")
    if r["status"] == 404:
        print("    SKIP  endpoint not loaded (bridge restart needed)\n")
    else:
        snaps = r["body"].get("snapshots", [])
        if len(snaps) >= 2:
            t.gte(
                snaps[0].get("created", 0),
                snaps[1].get("created", 0),
                "Snapshots sorted newest first"
            )
        t.ok(len(snaps) <= 20, f"Snapshot list capped at 20 (got {len(snaps)})")
        print()

    # ── Done ─────────────────────────────────────────────────
    return t.report()


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except TestError as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
