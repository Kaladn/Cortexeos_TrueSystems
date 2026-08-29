#!/usr/bin/env python3
"""
Agent Catalog Builder

Merges all contract-enriched category files into:
  - agent_catalog.csv        (full set)
  - truecore_agents.csv    (filtered safe set for TrueCore)
  - truecore_restricted.csv (blocked/sandbox set)
"""

import csv
import os
import hashlib
from collections import Counter

CONTRACTS_DIR = r"F:\contract_extraction\contracts"
OUTPUT_DIR = r"F:\contract_extraction"

CATEGORIES = [
    "engines", "controllers", "agents", "workers", "pipelines", "services",
    "retrievers", "validators", "transformers", "storage", "extractors",
]

CATALOG_FIELDS = [
    "operator_id", "name", "category", "agent_tier", "definition",
    "input_shape", "output_shape", "assumptions_in", "assumptions_out",
    "side_effects", "dependencies", "statefulness", "sync_mode",
    "destruction_score", "risk_type", "risk_reason",
    "requires_confirmation", "sandbox_required",
    "promotion_ready", "contract_status", "category_confidence",
    "source_file",
]

TRUECORE_CATS = {"security", "audit", "observers", "validators", "retrievers", "engines"}


def build_operator_id(category, function_name, file_path, definition):
    """Deterministic operator ID: {category}_{function}_{hash8}"""
    raw = f"{file_path}|{function_name}|{definition}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    clean_fn = function_name.replace(".", "_").replace(" ", "_")
    return f"{category}_{clean_fn}_{h}"


def get_definition_text(row):
    """Build definition citation from available metadata."""
    fn = row.get("symbol_name", "")
    ds = row.get("definition_source", "")
    dt = row.get("definition_type", "")

    if dt == "docstring" or ds == "docstring":
        return f"[docstring] {fn}"
    elif dt == "inline_comment" or ds == "inline_comment":
        return f"[inline] {fn}"
    else:
        return f"[inferred] {fn}"


def main():
    all_rows = []

    # ── Merge all contract CSVs ─────────────────────────────────
    for cat in CATEGORIES:
        fpath = os.path.join(CONTRACTS_DIR, f"{cat}_contracts.csv")
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fp = row.get("file_path", "")
                fn = row.get("symbol_name", "")
                defn = get_definition_text(row)
                op_id = build_operator_id(cat, fn, fp, defn)

                catalog_row = {
                    "operator_id": op_id,
                    "name": fn,
                    "category": row.get("primary_category", cat),
                    "agent_tier": row.get("agent_tier", ""),
                    "definition": defn,
                    "input_shape": row.get("input_shape", "UNKNOWN"),
                    "output_shape": row.get("output_shape", "UNKNOWN"),
                    "assumptions_in": row.get("assumptions_in", "UNKNOWN"),
                    "assumptions_out": row.get("assumptions_out", "UNKNOWN"),
                    "side_effects": row.get("side_effects", "UNKNOWN"),
                    "dependencies": row.get("dependencies", "UNKNOWN"),
                    "statefulness": row.get("statefulness", "UNKNOWN"),
                    "sync_mode": row.get("sync_mode", "UNKNOWN"),
                    "destruction_score": row.get("destruction_score", "0"),
                    "risk_type": row.get("risk_type", "none"),
                    "risk_reason": row.get("risk_reason", "no_risk_indicators"),
                    "requires_confirmation": row.get("requires_confirmation", "NO"),
                    "sandbox_required": row.get("sandbox_required", "NO"),
                    "promotion_ready": row.get("promotion_ready", "NO"),
                    "contract_status": row.get("contract_status", "UNKNOWN"),
                    "category_confidence": row.get("category_confidence", "LOW"),
                    "source_file": fp,
                }
                all_rows.append(catalog_row)

    # ── Write agent_catalog.csv ─────────────────────────────────
    catalog_path = os.path.join(OUTPUT_DIR, "agent_catalog.csv")
    with open(catalog_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    # ── Filter into TrueCore vs Restricted ────────────────────
    truecore = []
    restricted = []

    for r in all_rows:
        cat = r["category"]
        promo = r["promotion_ready"]
        dscore = int(r["destruction_score"])
        conf = r["category_confidence"]
        sandbox = r["sandbox_required"]

        # Restricted: sandbox required, not promotable, or low confidence
        if sandbox == "YES" or promo == "NO" or conf == "LOW":
            restricted.append(r)
            continue

        # TrueCore: right category, promoted, safe enough
        if cat in TRUECORE_CATS and promo == "YES" and dscore <= 3:
            truecore.append(r)
        # Everything else stays in full catalog only

    sc_path = os.path.join(OUTPUT_DIR, "truecore_agents.csv")
    with open(sc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(truecore)

    rest_path = os.path.join(OUTPUT_DIR, "truecore_restricted.csv")
    with open(rest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(restricted)

    # ── Summary ─────────────────────────────────────────────────
    total = len(all_rows)
    safe_count = len(truecore)
    restricted_count = len(restricted)
    catalog_only = total - safe_count - restricted_count
    scores = [int(r["destruction_score"]) for r in all_rows]
    avg_score = sum(scores) / len(scores) if scores else 0

    cat_counts = Counter(r["category"] for r in all_rows)
    sc_cat_counts = Counter(r["category"] for r in truecore)
    tier_counts = Counter(r["agent_tier"] for r in all_rows)
    score_dist = Counter(int(r["destruction_score"]) for r in all_rows)

    sc_score_dist = Counter(int(r["destruction_score"]) for r in truecore)
    rest_score_dist = Counter(int(r["destruction_score"]) for r in restricted)

    print("=" * 60)
    print("AGENT CATALOG BUILD COMPLETE")
    print("=" * 60)
    print()
    print(f"Total agents in catalog:        {total}")
    print(f"TrueCore safe agents:         {safe_count}")
    print(f"Restricted (blocked):           {restricted_count}")
    print(f"Catalog only (other cats):      {catalog_only}")
    print(f"Average destruction score:      {avg_score:.2f}")
    print()

    print("Destruction score distribution (full catalog):")
    labels = ["Safe", "Low", "Moderate", "Elevated", "High", "Critical"]
    for s in range(6):
        c = score_dist.get(s, 0)
        bar = "#" * (c // 20)
        print(f"  {s} ({labels[s]:10s}): {c:>5}  {bar}")

    print()
    print("Full catalog by category:")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat:25s} {cnt:>5}")

    print()
    print("TrueCore agents by category:")
    for cat, cnt in sc_cat_counts.most_common():
        print(f"  {cat:25s} {cnt:>5}")

    print()
    print("TrueCore destruction scores:")
    for s in range(6):
        c = sc_score_dist.get(s, 0)
        if c > 0:
            print(f"  {s} ({labels[s]:10s}): {c:>5}")

    print()
    print("By agent tier:")
    for tier, cnt in tier_counts.most_common():
        print(f"  {tier:20s} {cnt:>5}")

    print()
    print("Restricted reasons sample:")
    rest_reasons = Counter()
    for r in restricted:
        if r["sandbox_required"] == "YES":
            rest_reasons["sandbox_required"] += 1
        elif r["promotion_ready"] == "NO":
            rest_reasons["not_promotable"] += 1
        elif r["category_confidence"] == "LOW":
            rest_reasons["low_confidence"] += 1
    for reason, cnt in rest_reasons.most_common():
        print(f"  {reason:25s} {cnt:>5}")

    print()
    print("Output files:")
    print(f"  {catalog_path}")
    print(f"  {sc_path}")
    print(f"  {rest_path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
