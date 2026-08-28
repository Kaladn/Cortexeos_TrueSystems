from __future__ import annotations

from .schemas import ANCHOR_GROUP_NAMES


AFFECT_ANCHORS = (
    "garbage",
    "junk",
    "broken",
    "useless",
    "trash",
    "sick of",
    "fed up",
    "bullshit",
    "wrong",
    "nightmare",
)

URGENCY_ANCHORS = (
    "now",
    "right now",
    "quick",
    "urgent",
    "asap",
    "immediately",
    "client waiting",
    "deadline",
)

CONFUSION_ANCHORS = (
    "i don't know",
    "what is this",
    "why",
    "how",
    "unclear",
    "confused",
    "doesn't make sense",
)

CARE_PRIORITY_ANCHORS = (
    "protect",
    "backup",
    "back up",
    "preserve",
    "do not lose",
    "important",
    "my project",
    "project matters",
    "my family",
    "my daughter",
    "production",
    "main branch",
)

THREAT_ANCHORS = (
    "blow up",
    "burn",
    "kill",
    "hurt",
    "destroy",
    "punch",
    "attack",
)

COMMAND_ANCHORS = (
    "add",
    "audit",
    "back up",
    "backup",
    "build",
    "check",
    "commit",
    "compare",
    "delete",
    "fix",
    "get",
    "inspect",
    "open",
    "prove",
    "read",
    "remove",
    "restore",
    "run",
    "show",
    "start",
    "test",
    "trace",
    "write",
)

TARGET_ANCHORS = (
    "branch",
    "citation",
    "citations",
    "count",
    "counts",
    "dataset",
    "dataset id",
    "file",
    "file path",
    "folder",
    "main branch",
    "receipt",
    "receipt files",
    "repo",
    "repository",
    "runtime",
    "score",
    "status",
    "trace",
)

AMBIGUITY_ANCHORS = (
    "all",
    "everything",
    "it",
    "this",
    "that",
    "the whole thing",
    "the folder",
    "the repo",
)

EVIDENCE_ANCHORS = (
    "prove",
    "receipt",
    "citation",
    "citations",
    "where did it come from",
    "show the score",
    "show the weight",
    "score",
    "weight",
    "trace",
    "audit",
    "support",
    "evidence",
)

MUTATION_ANCHORS = (
    "delete",
    "remove",
    "wipe",
    "clear",
    "purge",
    "overwrite",
    "reset",
    "destroy",
    "trash",
    "nuke",
)

ANCHOR_GROUPS = {
    "affect_anchors": AFFECT_ANCHORS,
    "command_anchors": COMMAND_ANCHORS,
    "target_anchors": TARGET_ANCHORS,
    "risk_anchors": URGENCY_ANCHORS + THREAT_ANCHORS + CONFUSION_ANCHORS,
    "care_priority_anchors": CARE_PRIORITY_ANCHORS,
    "ambiguity_anchors": AMBIGUITY_ANCHORS,
    "evidence_anchors": EVIDENCE_ANCHORS,
    "mutation_anchors": MUTATION_ANCHORS,
}


def extract_anchor_groups(raw_input: str) -> dict[str, list[str]]:
    lowered = raw_input.lower()
    return {
        group_name: [anchor for anchor in ANCHOR_GROUPS[group_name] if _anchor_present(lowered, anchor)]
        for group_name in ANCHOR_GROUP_NAMES
    }


def _anchor_present(lowered_input: str, anchor: str) -> bool:
    lowered_anchor = anchor.lower()
    if " " in lowered_anchor:
        return lowered_anchor in lowered_input
    start = 0
    while True:
        index = lowered_input.find(lowered_anchor, start)
        if index < 0:
            return False
        before = lowered_input[index - 1] if index > 0 else " "
        after_index = index + len(lowered_anchor)
        after = lowered_input[after_index] if after_index < len(lowered_input) else " "
        if not _anchor_char(before) and not _anchor_char(after):
            return True
        start = index + 1


def _anchor_char(value: str) -> bool:
    return value.isalnum() or value in {"_", "'"}
