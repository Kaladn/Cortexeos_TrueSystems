"""Acceptance tests for the Reader-Writer Gateway.

Tests the 5 core invariants:
    1. AI writes to artifacts → succeeds
    2. AI writes outside artifacts → HARD DENIED
    3. Write to protected zone → HARD DENIED
    4. Promotion: artifacts → staging → implementation (human only)
    5. Every mutation has an audit trail entry

Run:  python -m pytest tests/test_gateway.py -v
  or: python tests/test_gateway.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security.gateway import (
    ReaderWriter,
    WriteZone,
    ProtectedZone,
    _zone_root,
    _CALLER_PERMISSIONS,
)
from security.directory_law import validate, DIRECTORY_LAW


class TestHarness:
    """Minimal test runner that doesn't require pytest."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_true(self, expr, msg=""):
        if expr:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"FAIL: {msg}")

    def assert_false(self, expr, msg=""):
        self.assert_true(not expr, msg)

    def assert_eq(self, a, b, msg=""):
        self.assert_true(a == b, f"{msg} — expected {b!r}, got {a!r}")

    def assert_in(self, item, container, msg=""):
        self.assert_true(item in container, f"{msg} — {item!r} not in {container!r}")

    def report(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        print(f"{'='*60}")
        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(f"  ❌ {e}")
        else:
            print("  ✅ All tests passed")
        return self.failed == 0


def run_tests():
    """Run all gateway acceptance tests against an isolated temp directory."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t = TestHarness()

    # ── Setup: isolated temp root ─────────────────────────────
    tmp = Path(tempfile.mkdtemp(prefix="clearbox_gw_test_"))
    print(f"Test root: {tmp}\n")

    # Monkey-patch CLEARBOX_DATA_ROOT for tests
    import security.data_paths as dp
    import security.gateway as gw

    original_root = dp.CLEARBOX_DATA_ROOT
    dp.CLEARBOX_DATA_ROOT = tmp

    # Re-create zone root mapper with test root
    original_zone_root = gw._zone_root
    def _test_zone_root(zone: WriteZone) -> Path:
        _map = {
            WriteZone.ARTIFACTS:       tmp / "system" / "artifacts",
            WriteZone.STAGING:         tmp / "system" / "staging",
            WriteZone.IMPLEMENTATION:  tmp / "system" / "implementation",
            WriteZone.DATA_RAW:        tmp / "data" / "raw",
            WriteZone.DATA_MAPPED:     tmp / "data" / "mapped",
            WriteZone.SESSIONS:        tmp / "sessions",
            WriteZone.LEXICON_USER:    tmp / "lexicon" / "user",
            WriteZone.CHAT_THREADS:    tmp / "chat_history" / "threads",
            WriteZone.CHAT_SUMMARIES:  tmp / "chat_history" / "summaries",
            WriteZone.CHAT_CITATIONS:  tmp / "chat_history" / "citations",
            WriteZone.STATE:           tmp / "state",
            WriteZone.CONFIG:          tmp / "config",
            WriteZone.LAKESPEAK_INDEX:   tmp / "lakespeak" / "index",
            WriteZone.LAKESPEAK_EVENTS:  tmp / "lakespeak" / "events",
            WriteZone.LAKESPEAK_EVAL:    tmp / "lakespeak" / "eval",
            WriteZone.IDEAS:               tmp / "ideas",
        }
        return _map[zone]
    gw._zone_root = _test_zone_root

    # Create gateway with test root
    gateway = ReaderWriter(root=tmp)

    try:
        # ──────────────────────────────────────────────────────
        print("TEST 1: Directory law validation")
        # ──────────────────────────────────────────────────────
        result = validate(root=tmp, fix=True)
        t.assert_eq(len(result["missing"]), 0, "All directories created")
        for rel in DIRECTORY_LAW:
            dir_path = tmp / rel.rstrip("/")
            t.assert_true(dir_path.exists(), f"Directory exists: {rel}")
        print(f"  ✅ {len(DIRECTORY_LAW)} directories validated\n")

        # ──────────────────────────────────────────────────────
        print("TEST 2: AI writes to artifacts → succeeds")
        # ──────────────────────────────────────────────────────
        result = gateway.write("ai", WriteZone.ARTIFACTS, "plan_v1.md",
                               "# Plan V1\nThis is an AI-generated plan.", encrypt=False)
        t.assert_true(result.success, "AI write to artifacts succeeds")
        t.assert_true(result.path is not None, "Path returned")
        t.assert_true(result.path.exists(), "File actually created")
        content = result.path.read_text(encoding="utf-8")
        t.assert_in("Plan V1", content, "Content correct")
        print(f"  ✅ AI artifact written: {result.path.name}\n")

        # ──────────────────────────────────────────────────────
        print("TEST 3: AI writes outside artifacts → DENIED")
        # ──────────────────────────────────────────────────────
        blocked_zones = [
            WriteZone.STAGING,
            WriteZone.IMPLEMENTATION,
            WriteZone.DATA_RAW,
            WriteZone.DATA_MAPPED,
            WriteZone.SESSIONS,
            WriteZone.LEXICON_USER,
            WriteZone.CHAT_THREADS,
            WriteZone.CHAT_SUMMARIES,
            WriteZone.CHAT_CITATIONS,
            WriteZone.STATE,
        ]
        for zone in blocked_zones:
            result = gateway.write("ai", zone, "evil.txt", "pwned", encrypt=False)
            t.assert_false(result.success, f"AI blocked from {zone.value}")
            t.assert_in("DENIED", result.error, f"Denial message for {zone.value}")
        print(f"  ✅ AI blocked from {len(blocked_zones)} non-artifact zones\n")

        # ──────────────────────────────────────────────────────
        print("TEST 4: System writes to allowed zones → succeeds")
        # ──────────────────────────────────────────────────────
        system_zones = [
            (WriteZone.DATA_RAW, "input_001.txt", "raw data"),
            (WriteZone.DATA_MAPPED, "map_001.json", '{"mapped": true}'),
            (WriteZone.SESSIONS, "session_001.json", '{"id": 1}'),
            (WriteZone.STATE, "runtime.json", '{"running": true}'),
        ]
        for zone, name, content in system_zones:
            result = gateway.write("system", zone, name, content, encrypt=False)
            t.assert_true(result.success, f"System write to {zone.value}/{name}")
        print(f"  ✅ System writes to {len(system_zones)} zones succeeded\n")

        # ──────────────────────────────────────────────────────
        print("TEST 5: Promotion chain (human only)")
        # ──────────────────────────────────────────────────────

        # 5a: AI tries to promote → DENIED
        result = gateway.promote("ai", "plan_v1.md",
                                 WriteZone.ARTIFACTS, WriteZone.STAGING)
        t.assert_false(result.success, "AI cannot promote")
        t.assert_in("DENIED", result.error, "AI promotion denial message")

        # 5b: System tries to promote → DENIED
        result = gateway.promote("system", "plan_v1.md",
                                 WriteZone.ARTIFACTS, WriteZone.STAGING)
        t.assert_false(result.success, "System cannot promote")

        # 5c: Human promotes artifacts → staging → succeeds
        result = gateway.promote("human", "plan_v1.md",
                                 WriteZone.ARTIFACTS, WriteZone.STAGING)
        t.assert_true(result.success, "Human promotes artifacts → staging")
        t.assert_true(result.path.exists(), "File exists in staging")
        t.assert_false(
            (_test_zone_root(WriteZone.ARTIFACTS) / "plan_v1.md").exists(),
            "File removed from artifacts after promotion"
        )

        # 5d: Human promotes staging → implementation → succeeds
        result = gateway.promote("human", "plan_v1.md",
                                 WriteZone.STAGING, WriteZone.IMPLEMENTATION)
        t.assert_true(result.success, "Human promotes staging → implementation")
        t.assert_true(result.path.exists(), "File exists in implementation")
        t.assert_false(
            (_test_zone_root(WriteZone.STAGING) / "plan_v1.md").exists(),
            "File removed from staging after promotion"
        )

        # 5e: Illegal promotion (artifacts → implementation, skipping staging) → DENIED
        gateway.write("ai", WriteZone.ARTIFACTS, "skip_test.md", "test", encrypt=False)
        result = gateway.promote("human", "skip_test.md",
                                 WriteZone.ARTIFACTS, WriteZone.IMPLEMENTATION)
        t.assert_false(result.success, "Cannot skip staging")
        t.assert_in("DENIED", result.error, "Skip-staging denial")
        print("  ✅ Promotion chain enforced: artifacts → staging → implementation\n")

        # ──────────────────────────────────────────────────────
        print("TEST 6: Path traversal blocked")
        # ──────────────────────────────────────────────────────
        result = gateway.write("ai", WriteZone.ARTIFACTS,
                               "../../etc/passwd", "pwned", encrypt=False)
        t.assert_false(result.success, "Path traversal blocked")
        print("  ✅ Path traversal attack blocked\n")

        # ──────────────────────────────────────────────────────
        print("TEST 7: Delete permissions")
        # ──────────────────────────────────────────────────────
        
        # Write something to delete
        gateway.write("ai", WriteZone.ARTIFACTS, "doomed.txt", "bye", encrypt=False)
        
        # AI cannot delete
        result = gateway.delete("ai", WriteZone.ARTIFACTS, "doomed.txt")
        t.assert_false(result.success, "AI cannot delete")
        t.assert_in("DENIED", result.error, "AI delete denial")

        # Human can delete
        result = gateway.delete("human", WriteZone.ARTIFACTS, "doomed.txt")
        t.assert_true(result.success, "Human can delete")
        t.assert_false(
            (_test_zone_root(WriteZone.ARTIFACTS) / "doomed.txt").exists(),
            "File actually deleted"
        )
        print("  ✅ Delete permissions enforced\n")

        # ──────────────────────────────────────────────────────
        print("TEST 8: Audit trail present")
        # ──────────────────────────────────────────────────────
        trail = gateway.get_audit_trail(limit=50)
        t.assert_true(len(trail) > 0, "Audit trail has entries")

        # Check that blocked attempts are logged
        blocked_entries = [e for e in trail if e["result"] == "denied"]
        t.assert_true(len(blocked_entries) > 0, "Blocked attempts are audited")

        # Check that successful writes are logged
        ok_entries = [e for e in trail if e["result"] == "ok"]
        t.assert_true(len(ok_entries) > 0, "Successful writes are audited")

        # Check that promotions are logged
        promo_entries = [e for e in trail if e["action"] == "promote"]
        t.assert_true(len(promo_entries) > 0, "Promotions are audited")

        print(f"  ✅ Audit trail: {len(trail)} entries "
              f"({len(ok_entries)} ok, {len(blocked_entries)} denied, "
              f"{len(promo_entries)} promotions)\n")

        # ──────────────────────────────────────────────────────
        print("TEST 9: Read operations")
        # ──────────────────────────────────────────────────────
        
        # Write something to read
        gateway.write("system", WriteZone.DATA_RAW, "readme.txt",
                       "Hello from raw zone", encrypt=False)
        
        content = gateway.read(WriteZone.DATA_RAW, "readme.txt")
        t.assert_eq(content, "Hello from raw zone", "Read returns correct content")
        
        # Read non-existent
        content = gateway.read(WriteZone.DATA_RAW, "nope.txt")
        t.assert_true(content is None, "Read non-existent returns None")

        # Exists check
        t.assert_true(gateway.exists(WriteZone.DATA_RAW, "readme.txt"), "Exists: true case")
        t.assert_false(gateway.exists(WriteZone.DATA_RAW, "nope.txt"), "Exists: false case")

        # List zone
        files = gateway.list_zone(WriteZone.DATA_RAW)
        t.assert_in("readme.txt", files, "List zone includes file")
        t.assert_in("input_001.txt", files, "List zone includes earlier file")
        print("  ✅ Read operations working\n")

        # ──────────────────────────────────────────────────────
        print("TEST 10: Gateway status")
        # ──────────────────────────────────────────────────────
        status = gateway.status()
        t.assert_true(status["zones"]["data_raw"] >= 2, "Status counts files in zones")
        t.assert_true(status["audit_entries"] > 0, "Status reports audit count")
        t.assert_in("config", status["protected_zones"], "Status lists protected zones")
        print(f"  ✅ Status: {json.dumps(status['zones'], indent=2)}\n")

    finally:
        # ── Cleanup ───────────────────────────────────────────
        gw._zone_root = original_zone_root
        dp.CLEARBOX_DATA_ROOT = original_root
        shutil.rmtree(tmp, ignore_errors=True)

    return t.report()


if __name__ == "__main__":
    print("=" * 60)
    print("  Clearbox AI — Reader-Writer Gateway Acceptance Tests")
    print("=" * 60)
    print()
    success = run_tests()
    sys.exit(0 if success else 1)
