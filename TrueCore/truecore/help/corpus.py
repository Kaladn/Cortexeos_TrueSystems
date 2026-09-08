"""Manual help corpus for TrueCore."""

from __future__ import annotations

import json
import ast
import hashlib
from typing import Any

from truecore.help.config import load_help_config


class HelpCorpus:
    def __init__(self):
        self._config = load_help_config()
        self._entries = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        from truecore.help.agent_usage import load_entries
        path = self._config["content_path"]
        entries = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                entries = json.load(handle)
        # Authored entries select files only. Never expose their behavioral prose.
        for help_id, old in list(entries.items()):
            facts = []
            for relative in old.get("tier3", {}).get("files", []):
                source = (self._config["repo_root"] / relative).resolve()
                if not source.is_relative_to(self._config["repo_root"].resolve()) or source.suffix != '.py' or not source.is_file():
                    facts.append({"path": relative, "status": "UNRESOLVED"})
                    continue
                raw = source.read_bytes()
                text = raw.decode('utf-8')
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    facts.append({"path": relative, "status": "SYNTAX_ERROR"})
                    continue
                facts.append({"path": relative, "status": "STATIC_CODE_FACTS_ONLY",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "definitions": [{"name": n.name, "line": n.lineno, "end_line": n.end_lineno,
                                     "source": ast.get_source_segment(text, n)}
                                    for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]})
            entries[help_id] = {"label": help_id, "category": "Code-derived help",
                "tier1": {"what": ', '.join(f['path'] for f in facts), "when": "STATIC_CODE_FACTS_ONLY"},
                "tier2": {"concept": "Behavior, permissions and safe invocation remain unresolved without executable contracts."},
                "tier3": {"how": json.dumps(facts, sort_keys=True)}, "code_facts": facts}
        generated = load_entries(self._config["agent_dir"])
        if set(entries) & set(generated):
            raise ValueError("manual help must not shadow agent usage")
        entries.update(generated)
        return entries

    def get(self, help_id: str) -> dict[str, Any] | None:
        return self._entries.get(help_id)

    def list_ids(self) -> list[dict[str, str]]:
        return [
            {
                "help_id": help_id,
                "label": entry.get("label", ""),
                "category": entry.get("category", ""),
            }
            for help_id, entry in sorted(self._entries.items())
        ]

    def search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower().strip()
        if not q:
            return []
        results = []
        for help_id, entry in self._entries.items():
            searchable = " ".join([
                help_id,
                entry.get("label", ""),
                entry.get("category", ""),
                json.dumps(entry.get("tier1", {}), sort_keys=True),
                json.dumps(entry.get("tier2", {}), sort_keys=True),
                json.dumps(entry.get("tier3", {}), sort_keys=True),
            ]).lower()
            if q in searchable:
                results.append({
                    "source": "corpus",
                    "help_id": help_id,
                    "label": entry.get("label", ""),
                    "category": entry.get("category", ""),
                    "snippet": entry.get("tier1", {}).get("what", "")[:120],
                })
        return results

    def stats(self) -> dict[str, Any]:
        categories: dict[str, int] = {}
        for entry in self._entries.values():
            category = entry.get("category", "Uncategorized")
            categories[category] = categories.get(category, 0) + 1
        return {
            "total_ids": len(self._entries),
            "categories": categories,
        }
