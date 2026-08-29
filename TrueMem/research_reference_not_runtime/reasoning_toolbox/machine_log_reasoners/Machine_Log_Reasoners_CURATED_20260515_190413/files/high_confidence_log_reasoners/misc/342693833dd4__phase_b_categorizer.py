#!/usr/bin/env python3
"""
Phase B: Category Split Agent
Reads extraction_scan.csv, categorizes PAIRED rows, splits into category files.
"""

import csv
import os
import re
from collections import Counter, defaultdict

INPUT_FILE = r"F:\contract_extraction\extraction_scan.csv"
OUTPUT_DIR = r"F:\contract_extraction"
CAT_DIR = os.path.join(OUTPUT_DIR, "categories")

os.makedirs(CAT_DIR, exist_ok=True)

# ============================================================================
# CATEGORY CLASSIFICATION RULES
# ============================================================================

# Keywords mapped to categories, checked in priority order (first match wins)
# More specific patterns first, broader ones last
CATEGORY_RULES = [
    # --- STANDALONE TIER ---
    ("agents", [
        r'\bagent\b', r'_agent$', r'^agent_', r'Agent\.',
    ]),
    ("pipelines", [
        r'\bpipeline\b', r'_pipeline$', r'^pipeline_', r'\bstaged_process\b',
    ]),
    ("workers", [
        r'\bworker\b', r'_worker$', r'^worker_', r'\bdaemon\b', r'\bbackground_task\b',
        r'\basync_loop\b', r'\btask_loop\b',
    ]),
    ("services", [
        r'\bservice\b', r'_service$', r'^service_', r'\bserve\b', r'\bserver\b',
        r'^start_server', r'^stop_server',
    ]),
    ("controllers", [
        r'\bcontroller\b', r'\borchestrat', r'\bcommand_', r'\bdispatch_',
        r'\bstate_machine\b', r'\bcoordinator\b', r'^manage_', r'\bmanager\b',
    ]),
    ("engines", [
        r'\bengine\b', r'_engine$', r'^engine_', r'\bcognition\b', r'\blexicon\b',
        r'\breasoning\b', r'\breaper\b', r'\bcortex\b', r'\bneural\b',
        r'\bresonance\b', r'\bfabric\b', r'\bkernel\b',
    ]),

    # --- OPERATOR TIER ---
    ("security", [
        r'\bauth\b', r'\bpermission\b', r'\btrust\b', r'\bpolicy\b', r'\baccess_control\b',
        r'\bencrypt\b', r'\bdecrypt\b', r'\bhoneypot\b', r'\bfirewall\b', r'\bguardian\b',
        r'\bsession\b', r'\btoken_valid', r'\bjwt\b', r'\brbac\b', r'\bgating\b',
        r'\bsecurity\b', r'\bdeception\b', r'\bforensic\b', r'\bdefense\b',
        r'\bsandbox\b', r'\bquarantine\b', r'\bthreat\b', r'\banomaly\b',
        r'\bsignature_detect\b', r'\bintrusion\b',
    ]),
    ("audit", [
        r'\baudit\b', r'\bprovenance\b', r'\btrace\b', r'\bhistory\b',
        r'\blog_event\b', r'\breport\b', r'\brecord_action\b', r'\bjournal\b',
        r'\bcheckpoint\b',
    ]),
    ("observers", [
        r'\bmonitor\b', r'\bwatch\b', r'\bobserv', r'\bsensor\b', r'\bmetric\b',
        r'\bcollect\b', r'\bprobe\b', r'\bhealth_check\b', r'\bstatus\b',
        r'\btrack\b', r'\bpoll\b',
    ]),
    ("parsers", [
        r'\bparse\b', r'\btokeniz', r'\blex\b', r'\bdeserializ', r'\bread_format\b',
        r'\bfrom_json\b', r'\bfrom_binary\b', r'\bfrom_xml\b', r'\bfrom_csv\b',
        r'\bdecode\b', r'\bunmarshal\b',
    ]),
    ("extractors", [
        r'\bextract\b', r'\bpull_', r'\bscrape\b', r'\bcapture\b', r'\bharvest\b',
        r'\bmine_', r'\bget_features\b', r'\bget_entities\b', r'\bget_fields\b',
    ]),
    ("transformers", [
        r'\btransform\b', r'\bconvert\b', r'\bmap_', r'\bnormaliz', r'\bsanitiz',
        r'\bencode\b', r'\bcompress\b', r'\bdecompress\b', r'\btranslat',
        r'\breshape\b', r'\bflatten\b', r'\bembed\b', r'\bvectoriz',
    ]),
    ("validators", [
        r'\bvalidat', r'\bverif', r'\bcheck_', r'\bassert_', r'\bensure_',
        r'\bis_valid\b', r'\bconfirm\b', r'\binspect\b', r'\btest_',
        r'\bconstraint\b',
    ]),
    ("routers", [
        r'\broute\b', r'\brouter\b', r'\bdispatch\b', r'\bforward\b',
        r'\bdirect\b', r'\bredirect\b',
    ]),
    ("selectors", [
        r'\bselect\b', r'\bchoose\b', r'\bpick\b', r'\bbest_', r'\brank\b',
        r'\bfilter\b', r'\bsort\b', r'\bprioritiz', r'\bmatch\b',
        r'\brecommend\b', r'\bcandidate\b',
    ]),
    ("formatters", [
        r'\bformat\b', r'\brender\b', r'\bserializ', r'\bto_json\b', r'\bto_binary\b',
        r'\bto_csv\b', r'\bto_xml\b', r'\bto_string\b', r'\bpretty_print\b',
        r'\btemplate\b', r'\bdisplay\b', r'\bpresent\b',
    ]),
    ("retrievers", [
        r'\bretriев', r'\bfetch\b', r'\bsearch\b', r'\bquery\b', r'\blookup\b',
        r'\bfind\b', r'\bget_by_', r'\bload_from\b', r'\bresolve\b',
        r'\bseek\b',
    ]),
    ("storage", [
        r'\bsave\b', r'\bstore\b', r'\bpersist\b', r'\bwrite_to\b', r'\bflush\b',
        r'\bcommit\b', r'\binsert\b', r'\bupdate_record\b', r'\bdelete_record\b',
        r'\bbackup\b', r'\brestore\b', r'\bcache\b', r'\bsave_to\b',
    ]),
    ("executors", [
        r'\bexecut', r'\brun_', r'\binvok', r'\bcall_', r'\blaunch\b',
        r'\bspawn\b', r'\bfire\b', r'\btrigger\b', r'\bperform\b',
    ]),

    # --- SUPPORT TIER ---
    ("shim_candidates", [
        r'\badapt', r'\bbridg', r'\bwrapper\b', r'\bshim\b', r'\bcompat\b',
        r'\bproxy\b', r'\bmiddleware\b', r'\binterface\b', r'\bfacade\b',
        r'\bconverter\b', r'\btranslator\b',
    ]),
    ("legacy", [
        r'\bdeprecated\b', r'\bold_', r'\blegacy\b', r'\bfrozen\b',
        r'\b_v[0-9]\b', r'\barchive\b', r'\bobsolete\b',
    ]),
    ("support", [
        r'\bsetup\b', r'\bteardown\b', r'\bcleanup\b', r'\breset\b',
        r'\bclear\b', r'\binit\b', r'\bconfigure\b', r'\bclose\b',
        r'\bopen\b', r'\bconnect\b', r'\bdisconnect\b', r'\b_helper\b',
        r'\b_util\b', r'\bregister\b', r'\bsubscribe\b', r'\bunsubscribe\b',
        r'\bon_start\b', r'\bon_stop\b', r'\bon_error\b',
    ]),
]

# Agent tier mapping
TIER_MAP = {
    "engines": "standalone",
    "controllers": "standalone",
    "agents": "standalone",
    "workers": "standalone",
    "pipelines": "standalone",
    "services": "standalone",
    "parsers": "operator",
    "extractors": "operator",
    "transformers": "operator",
    "validators": "operator",
    "routers": "operator",
    "selectors": "operator",
    "formatters": "operator",
    "retrievers": "operator",
    "storage": "operator",
    "executors": "operator",
    "observers": "operator",
    "security": "operator",
    "audit": "operator",
    "support": "support",
    "shim_candidates": "support",
    "legacy": "support",
    "unclassified": "unclassified",
}

# Confidence: HIGH if keyword is in symbol_name directly, MEDIUM if in file_path, LOW if inferred
def classify(row):
    symbol = row.get("symbol_name", "").lower()
    fpath = row.get("file_path", "").lower()
    combined = symbol + " " + fpath

    # Pass 1: Check symbol_name directly (HIGH confidence)
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, symbol):
                return category, "HIGH", f"symbol matches /{pattern}/"

    # Pass 2: Check symbol_name against broader action-verb patterns
    # These are too generic for standalone but map well to operator categories
    ACTION_VERBS = [
        ("parsers", [r'^parse_', r'^tokenize_', r'^decode_', r'^from_']),
        ("extractors", [r'^extract_', r'^pull_', r'^scrape_', r'^capture_', r'^harvest_', r'^mine_']),
        ("transformers", [r'^convert_', r'^map_', r'^normalize_', r'^encode_', r'^compress_',
                          r'^transform_', r'^translate_', r'^reshape_', r'^flatten_', r'^embed_']),
        ("validators", [r'^validate_', r'^verify_', r'^check_', r'^assert_', r'^ensure_', r'^is_valid']),
        ("formatters", [r'^format_', r'^render_', r'^serialize_', r'^to_json', r'^to_binary',
                        r'^to_csv', r'^to_string', r'^display_', r'^present_', r'^pretty_']),
        ("retrievers", [r'^fetch_', r'^search_', r'^query_', r'^lookup_', r'^find_',
                        r'^get_by_', r'^load_from', r'^resolve_', r'^seek_', r'^read_']),
        ("storage", [r'^save_', r'^store_', r'^persist_', r'^write_to', r'^flush_',
                     r'^commit_', r'^insert_', r'^backup_', r'^restore_', r'^cache_']),
        ("executors", [r'^execute_', r'^run_', r'^invoke_', r'^call_', r'^launch_',
                       r'^spawn_', r'^fire_', r'^trigger_', r'^perform_']),
        ("observers", [r'^monitor_', r'^watch_', r'^observe_', r'^track_', r'^poll_',
                       r'^collect_', r'^probe_', r'^measure_']),
        ("selectors", [r'^select_', r'^choose_', r'^pick_', r'^rank_', r'^filter_',
                       r'^sort_', r'^prioritize_', r'^match_', r'^best_']),
        ("security", [r'^auth_', r'^encrypt_', r'^decrypt_', r'^sign_', r'^hash_']),
        ("support", [r'^setup_', r'^teardown_', r'^cleanup_', r'^reset_', r'^clear_',
                     r'^init_', r'^configure_', r'^close_', r'^open_', r'^connect_',
                     r'^disconnect_', r'^register_']),
        ("transformers", [r'^clean_', r'^build_', r'^create_', r'^make_', r'^prepare_',
                          r'^compile_', r'^assemble_', r'^compose_']),
        ("retrievers", [r'^load_', r'^get_', r'^read_']),
    ]

    for category, patterns in ACTION_VERBS:
        for pattern in patterns:
            if re.search(pattern, symbol):
                return category, "HIGH", f"symbol verb matches /{pattern}/"

    # Pass 3: Classify by file_path context (MEDIUM confidence)
    # Methods inside engine/cortex/kernel files inherit the parent context
    FILE_CONTEXT = [
        ("engines", [r'\bengine\b', r'\bcortex', r'\bkernel\b', r'\bcognition\b',
                     r'\blexicon\b', r'\breasoning\b', r'\breaper\b', r'\bneural\b',
                     r'\bresonance\b', r'\bfabric\b', r'\bcascad', r'\bsymboli',
                     r'\bnlp\b', r'\bembedding\b', r'\bpredict\b']),
        ("security", [r'\bsecurity\b', r'\bauth\b', r'\bhoneypot\b', r'\bfirewall\b',
                      r'\bguardian\b', r'\bforensic\b', r'\bdeception\b', r'\bdefense\b',
                      r'\brbac\b', r'\baccess.control\b', r'\bthreat\b', r'\bnet_security\b']),
        ("agents", [r'\bagent\b', r'_agent\.py']),
        ("controllers", [r'\bcontroller\b', r'\borchestrat', r'\bmanager\b', r'\bdispatch\b']),
        ("services", [r'\bservice\b', r'\bserver\b', r'\bapi\b', r'\bapp\.py$', r'\broute']),
        ("pipelines", [r'\bpipeline\b']),
        ("observers", [r'\bmonitor\b', r'\bdashboard\b', r'\bmetric']),
        ("storage", [r'\bstorage\b', r'\bdatabase\b', r'\bdb\b', r'\bcache\b']),
        ("validators", [r'\bvalidat', r'\btest_', r'\bcheck\b']),
        ("shim_candidates", [r'\bbridge\b', r'\badapter\b', r'\bwrapper\b', r'\bmiddleware\b']),
        ("legacy", [r'\blegacy\b', r'\barchive\b', r'\bold_\b', r'\bdeprecated\b', r'\bbackup\b']),
        ("support", [r'\butil', r'\bhelper\b', r'\bconfig\b', r'\bsetup\b', r'\btool']),
    ]

    for category, patterns in FILE_CONTEXT:
        for pattern in patterns:
            if re.search(pattern, fpath):
                return category, "MEDIUM", f"file_path context matches /{pattern}/"

    # Pass 4: Check for common standalone method names on classes
    if '.' in row.get("symbol_name", ""):
        # It's a class method — check the class name portion
        class_name = row["symbol_name"].split('.')[0].lower()
        CLASS_KEYWORDS = [
            ("engines", ['engine', 'cortex', 'kernel', 'lexicon', 'neural', 'reaper',
                         'cognition', 'reasoning', 'resonance', 'fabric', 'cascade',
                         'symboli', 'tokenizer', 'embedding', 'model']),
            ("controllers", ['controller', 'orchestrator', 'manager', 'coordinator', 'dispatcher']),
            ("agents", ['agent']),
            ("workers", ['worker', 'daemon', 'runner']),
            ("services", ['service', 'server', 'api']),
            ("security", ['auth', 'guardian', 'firewall', 'security', 'policy', 'rbac']),
            ("validators", ['validator', 'checker', 'verifier']),
            ("parsers", ['parser', 'tokenizer', 'lexer', 'decoder']),
            ("storage", ['store', 'storage', 'repository', 'cache', 'database']),
            ("observers", ['monitor', 'observer', 'watcher', 'tracker', 'sensor']),
            ("transformers", ['transformer', 'converter', 'encoder', 'builder', 'generator']),
            ("shim_candidates", ['bridge', 'adapter', 'wrapper', 'proxy', 'shim']),
        ]
        for category, keywords in CLASS_KEYWORDS:
            for kw in keywords:
                if kw in class_name:
                    return category, "MEDIUM", f"class name '{class_name}' contains '{kw}'"

    return "unclassified", "LOW", "no pattern matched"


# ============================================================================
# MAIN PROCESSING
# ============================================================================

print("Phase B: Category Split Agent")
print("=" * 60)
print(f"Input:  {INPUT_FILE}")
print(f"Output: {OUTPUT_DIR}")
print()

# Read all rows
all_rows = []
with open(INPUT_FILE, "r", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    original_fields = reader.fieldnames[:]
    for row in reader:
        all_rows.append(row)

print(f"Total rows read: {len(all_rows)}")

# Split PAIRED vs FUNCTION_ONLY vs SKIP
paired_rows = [r for r in all_rows if r.get("status") == "PAIRED"]
funconly_rows = [r for r in all_rows if r.get("status") == "FUNCTION_ONLY"]
skip_rows = [r for r in all_rows if r.get("status") not in ("PAIRED", "FUNCTION_ONLY")]

print(f"  PAIRED:        {len(paired_rows)}")
print(f"  FUNCTION_ONLY: {len(funconly_rows)}")
print(f"  SKIP/other:    {len(skip_rows)}")
print()

# New columns
new_fields = original_fields + [
    "primary_category",
    "category_confidence",
    "agent_tier",
    "category_reason",
    "export_file",
]

# Classify each PAIRED row
category_buckets = defaultdict(list)
confidence_counts = Counter()
tier_counts = Counter()

for row in paired_rows:
    cat, conf, reason = classify(row)
    row["primary_category"] = cat
    row["category_confidence"] = conf
    row["agent_tier"] = TIER_MAP.get(cat, "unclassified")
    row["category_reason"] = reason
    row["export_file"] = f"categories/{cat}.csv"

    category_buckets[cat].append(row)
    confidence_counts[conf] += 1
    tier_counts[row["agent_tier"]] += 1

# ============================================================================
# WRITE OUTPUTS
# ============================================================================

def write_csv(filepath, fieldnames, rows):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

# 1. paired_only.csv — all paired rows with new columns
count = write_csv(os.path.join(OUTPUT_DIR, "paired_only.csv"), new_fields, paired_rows)
print(f"Wrote paired_only.csv: {count} rows")

# 2. function_only.csv — all FUNCTION_ONLY rows (original columns only)
count = write_csv(os.path.join(OUTPUT_DIR, "function_only.csv"), original_fields, funconly_rows)
print(f"Wrote function_only.csv: {count} rows")

# 3. Category files
print()
print("Category files:")
for cat_name in [
    "engines", "controllers", "agents", "workers", "pipelines", "services",
    "parsers", "extractors", "transformers", "validators", "routers",
    "selectors", "formatters", "retrievers", "storage", "executors",
    "observers", "security", "audit", "support", "shim_candidates",
    "legacy", "unclassified",
]:
    rows = category_buckets.get(cat_name, [])
    filepath = os.path.join(CAT_DIR, f"{cat_name}.csv")
    write_csv(filepath, new_fields, rows)
    print(f"  {cat_name}.csv: {len(rows)} rows")

# 4. category_index.csv
index_rows = []
for cat_name in sorted(category_buckets.keys()):
    rows = category_buckets[cat_name]
    high = sum(1 for r in rows if r["category_confidence"] == "HIGH")
    med = sum(1 for r in rows if r["category_confidence"] == "MEDIUM")
    low = sum(1 for r in rows if r["category_confidence"] == "LOW")
    index_rows.append({
        "primary_category": cat_name,
        "count": len(rows),
        "high_confidence_count": high,
        "medium_confidence_count": med,
        "low_confidence_count": low,
        "agent_tier": TIER_MAP.get(cat_name, "unclassified"),
        "export_file": f"categories/{cat_name}.csv",
    })

index_fields = [
    "primary_category", "count", "high_confidence_count",
    "medium_confidence_count", "low_confidence_count",
    "agent_tier", "export_file",
]
write_csv(os.path.join(OUTPUT_DIR, "category_index.csv"), index_fields, index_rows)
print(f"\nWrote category_index.csv: {len(index_rows)} categories")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print()
print("=" * 60)
print("PHASE B FINAL SUMMARY")
print("=" * 60)
print(f"Total PAIRED rows processed:     {len(paired_rows)}")
print(f"Total FUNCTION_ONLY exported:    {len(funconly_rows)}")
print()

print("Count per category:")
for cat, rows in sorted(category_buckets.items(), key=lambda x: -len(x[1])):
    print(f"  {cat:25s} {len(rows):>5}")

print()
print("Count per agent_tier:")
for tier, count in tier_counts.most_common():
    print(f"  {tier:20s} {count:>5}")

print()
print("Confidence distribution:")
for conf, count in confidence_counts.most_common():
    print(f"  {conf:10s} {count:>5}")

print()
print("Top 10 largest categories:")
sorted_cats = sorted(category_buckets.items(), key=lambda x: -len(x[1]))
for i, (cat, rows) in enumerate(sorted_cats[:10]):
    tier = TIER_MAP.get(cat, "?")
    print(f"  {i+1:2d}. {cat:25s} {len(rows):>5} rows  [{tier}]")

low_confidence = sum(1 for r in paired_rows if r["category_confidence"] == "LOW")
print(f"\nLOW confidence rows requiring review: {low_confidence}")
print()
print("Phase B complete.")
