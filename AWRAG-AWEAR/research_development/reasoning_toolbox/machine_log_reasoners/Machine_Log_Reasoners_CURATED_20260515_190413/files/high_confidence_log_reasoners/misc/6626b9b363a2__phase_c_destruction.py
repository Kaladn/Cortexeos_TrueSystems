#!/usr/bin/env python3
"""
Phase C Extension: Destruction Scoring

Reads existing contract CSVs, adds destruction/risk scoring columns,
writes updated files back. Does NOT re-infer contracts — just adds
the safety layer on top of what Phase C already produced.

Usage:
    python phase_c_destruction.py
"""

import csv
import os
import re
from collections import Counter

CONTRACTS_DIR = r"F:\contract_extraction\contracts"

CATEGORIES = [
    "engines", "controllers", "agents", "workers", "pipelines", "services",
    "retrievers", "validators", "transformers", "storage", "extractors",
]

# New columns to add
DESTRUCTION_FIELDS = [
    "destruction_score",
    "risk_type",
    "risk_reason",
    "requires_confirmation",
    "sandbox_required",
]


# ============================================================================
# DESTRUCTION SCORING ENGINE
# ============================================================================

def score_destruction(row: dict) -> dict:
    """
    Score destruction potential based on side_effects, failure_modes,
    input_shape, output_shape, category, and function context.
    """
    side_effects = row.get("side_effects", "").lower()
    failure_modes = row.get("failure_modes", "").lower()
    symbol = row.get("symbol_name", "").lower()
    file_path = row.get("file_path", "").lower()
    category = row.get("primary_category", "").lower()
    input_shape = row.get("input_shape", "").lower()
    output_shape = row.get("output_shape", "").lower()
    statefulness = row.get("statefulness", "").upper()

    score = 0
    risk_types = set()
    reasons = []

    # ── SIDE EFFECT SCORING ─────────────────────────────────────

    # Disk operations
    if "disk" in side_effects:
        score += 2
        risk_types.add("filesystem")
        reasons.append("writes_to_disk")

    # Network
    if "network" in side_effects:
        score += 2
        risk_types.add("network")
        reasons.append("network_calls")

    # Database
    if "db" in side_effects:
        score += 2
        risk_types.add("data")
        reasons.append("database_operations")

    # Subprocess execution
    if "subprocess" in side_effects:
        score += 3
        risk_types.add("process")
        reasons.append("spawns_subprocess")

    # State mutation
    if "mutation" in side_effects:
        score += 1
        risk_types.add("data")
        reasons.append("mutates_state")

    # ── FUNCTION NAME PATTERN SCORING ───────────────────────────

    # Destructive verbs
    destructive_verbs = [
        (r'\bdelete\b', 3, "process", "delete_operation"),
        (r'\bremove\b', 3, "filesystem", "remove_operation"),
        (r'\bdrop\b', 3, "data", "drop_operation"),
        (r'\bdestroy\b', 4, "process", "destroy_operation"),
        (r'\bkill\b', 4, "process", "kill_operation"),
        (r'\bterminate\b', 3, "process", "terminate_operation"),
        (r'\bwipe\b', 4, "data", "wipe_operation"),
        (r'\bpurge\b', 4, "data", "purge_operation"),
        (r'\btruncate\b', 3, "data", "truncate_operation"),
        (r'\boverwrite\b', 3, "filesystem", "overwrite_operation"),
        (r'\breset\b', 2, "data", "reset_operation"),
        (r'\bclear\b', 2, "data", "clear_operation"),
        (r'\bformat\b', 2, "filesystem", "format_operation"),  # ambiguous with formatters
        (r'\bexec\b', 3, "process", "exec_operation"),
        (r'\beval\b', 4, "security", "eval_operation"),
        (r'\bshutdown\b', 3, "process", "shutdown_operation"),
        (r'\breboot\b', 4, "process", "reboot_operation"),
        (r'\bforce\b', 2, "process", "force_operation"),
    ]

    for pattern, s, rtype, reason in destructive_verbs:
        if re.search(pattern, symbol):
            score += s
            risk_types.add(rtype)
            reasons.append(reason)

    # Write/modify operations (lower risk than delete)
    write_verbs = [
        (r'\bwrite\b', 1, "filesystem", "write_operation"),
        (r'\bsave\b', 1, "filesystem", "save_operation"),
        (r'\bupdate\b', 1, "data", "update_operation"),
        (r'\binsert\b', 1, "data", "insert_operation"),
        (r'\bmodify\b', 1, "data", "modify_operation"),
        (r'\bpatch\b', 1, "data", "patch_operation"),
        (r'\bset_\b', 1, "data", "setter_operation"),
        (r'\bpush\b', 1, "network", "push_operation"),
        (r'\bsend\b', 1, "network", "send_operation"),
        (r'\bpost\b', 1, "network", "post_operation"),
        (r'\bdeploy\b', 2, "process", "deploy_operation"),
    ]

    for pattern, s, rtype, reason in write_verbs:
        if re.search(pattern, symbol):
            score += s
            risk_types.add(rtype)
            reasons.append(reason)

    # ── SECURITY CONTEXT ────────────────────────────────────────

    security_patterns = [
        (r'\bauth\b', 2, "security", "auth_related"),
        (r'\bpermission\b', 2, "security", "permission_related"),
        (r'\btoken\b', 1, "security", "token_handling"),
        (r'\bcredential\b', 3, "security", "credential_handling"),
        (r'\bpassword\b', 3, "security", "password_handling"),
        (r'\bsecret\b', 3, "security", "secret_handling"),
        (r'\bencrypt\b', 1, "security", "encryption"),
        (r'\bdecrypt\b', 2, "security", "decryption"),
        (r'\bbypass\b', 4, "security", "bypass_potential"),
        (r'\bescalat\b', 4, "security", "escalation_potential"),
        (r'\binject\b', 3, "security", "injection_risk"),
    ]

    for pattern, s, rtype, reason in security_patterns:
        if re.search(pattern, symbol) or re.search(pattern, file_path):
            score += s
            risk_types.add(rtype)
            reasons.append(reason)

    # ── FILE PATH CONTEXT ───────────────────────────────────────

    if any(p in file_path for p in ["security", "auth", "rbac", "guardian", "firewall"]):
        score += 1
        risk_types.add("security")
        reasons.append("security_module")

    if any(p in file_path for p in ["deception", "honeypot", "forensic"]):
        score += 1
        risk_types.add("security")
        reasons.append("active_defense_module")

    # ── FAILURE MODE ESCALATION ─────────────────────────────────

    if "raises_" in failure_modes and "subprocess" in side_effects:
        score += 1
        reasons.append("exception_in_subprocess_context")

    # ── STATEFULNESS RISK ───────────────────────────────────────

    if statefulness == "STATEFUL" and "mutation" in side_effects:
        score += 1
        reasons.append("stateful_mutation")

    # ── CATEGORY ADJUSTMENTS ────────────────────────────────────

    # Formatters that matched "format" verb — reduce score
    if category == "formatters" and "format_operation" in reasons:
        score -= 2
        reasons.remove("format_operation")
        reasons.append("formatter_not_destructive")

    # Pure parsers / validators with no side effects = safe
    if category in ("parsers", "validators") and side_effects in ("none", "logging"):
        score = max(score - 1, 0)

    # ── CLAMP AND DERIVE ────────────────────────────────────────

    score = max(0, min(5, score))

    # Determine confirmation and sandbox requirements
    requires_confirmation = "YES" if score >= 3 else "NO"
    sandbox_required = "YES" if score >= 4 else "NO"

    # Default risk type if none detected
    if not risk_types:
        risk_types.add("none")
    if not reasons:
        reasons.append("no_risk_indicators")

    return {
        "destruction_score": score,
        "risk_type": "|".join(sorted(risk_types)),
        "risk_reason": "|".join(reasons[:5]),  # cap at 5 reasons
        "requires_confirmation": requires_confirmation,
        "sandbox_required": sandbox_required,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("Phase C Extension: Destruction Scoring")
    print("=" * 60)

    grand_total = 0
    score_dist = Counter()
    risk_dist = Counter()
    confirm_count = 0
    sandbox_count = 0
    all_category_stats = []

    for cat in CATEGORIES:
        input_file = os.path.join(CONTRACTS_DIR, f"{cat}_contracts.csv")
        if not os.path.exists(input_file):
            print(f"  SKIP: {input_file} not found")
            continue

        # Read
        rows = []
        with open(input_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames[:]
            rows = list(reader)

        if not rows:
            continue

        # Add new fields to header
        output_fields = fields[:]
        for df in DESTRUCTION_FIELDS:
            if df not in output_fields:
                output_fields.append(df)

        # Score each row
        cat_scores = Counter()
        for row in rows:
            destruction = score_destruction(row)
            row.update(destruction)

            s = destruction["destruction_score"]
            score_dist[s] += 1
            cat_scores[s] += 1

            for rt in destruction["risk_type"].split("|"):
                if rt.strip():
                    risk_dist[rt.strip()] += 1

            if destruction["requires_confirmation"] == "YES":
                confirm_count += 1
            if destruction["sandbox_required"] == "YES":
                sandbox_count += 1

        # Write back
        with open(input_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        grand_total += len(rows)

        cat_stat = {
            "category": cat,
            "total": len(rows),
            "score_0": cat_scores.get(0, 0),
            "score_1": cat_scores.get(1, 0),
            "score_2": cat_scores.get(2, 0),
            "score_3": cat_scores.get(3, 0),
            "score_4": cat_scores.get(4, 0),
            "score_5": cat_scores.get(5, 0),
        }
        all_category_stats.append(cat_stat)

        print(f"  {cat:25s}  {len(rows):>5} rows  "
              f"safe(0-1)={cat_scores.get(0,0)+cat_scores.get(1,0):>5}  "
              f"mod(2)={cat_scores.get(2,0):>5}  "
              f"elev(3)={cat_scores.get(3,0):>5}  "
              f"high(4)={cat_scores.get(4,0):>5}  "
              f"crit(5)={cat_scores.get(5,0):>5}")

    # Write destruction index
    index_file = os.path.join(CONTRACTS_DIR, "destruction_index.csv")
    with open(index_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "category", "total", "score_0", "score_1", "score_2",
            "score_3", "score_4", "score_5"
        ])
        writer.writeheader()
        writer.writerows(all_category_stats)

    # Final summary
    print()
    print("=" * 60)
    print("DESTRUCTION SCORING SUMMARY")
    print("=" * 60)
    print(f"Total rows scored:            {grand_total}")
    print()
    print("Score distribution:")
    for s in range(6):
        label = ["Safe", "Low", "Moderate", "Elevated", "High", "Critical"][s]
        count = score_dist.get(s, 0)
        bar = "#" * (count // 20)
        print(f"  {s} ({label:10s}): {count:>5}  {bar}")

    print()
    print("Risk type distribution:")
    for rt, cnt in risk_dist.most_common():
        print(f"  {rt:20s}  {cnt:>5}")

    print()
    print(f"Requires confirmation (score >= 3):  {confirm_count}")
    print(f"Requires sandbox (score >= 4):       {sandbox_count}")

    safe = score_dist.get(0, 0) + score_dist.get(1, 0)
    moderate = score_dist.get(2, 0)
    dangerous = score_dist.get(3, 0) + score_dist.get(4, 0) + score_dist.get(5, 0)

    print()
    print(f"SAFE (0-1):      {safe:>5}  ({safe/grand_total*100:.1f}%)")
    print(f"MODERATE (2):    {moderate:>5}  ({moderate/grand_total*100:.1f}%)")
    print(f"DANGEROUS (3-5): {dangerous:>5}  ({dangerous/grand_total*100:.1f}%)")
    print()
    print(f"Destruction index written to: {index_file}")
    print("Phase C Extension complete.")


if __name__ == "__main__":
    main()
