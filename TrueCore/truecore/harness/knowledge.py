"""Deterministic TrueCore knowledge and creator harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from truecore.harness.factories import factory_blueprints
from truecore.tools.capabilities import build_default_capability_registry
from truecore.tools.recipes import build_default_chain_recipes
from truecore.worker_feeds.registry import default_worker_registry


@dataclass(frozen=True)
class HarnessIntent:
    intent: str
    target_kind: str
    needed_capabilities: tuple[str, ...]
    confidence: float


class TrueCoreHarness:
    """Read-only creator/security harness for TrueCore.

    The harness selects capability requirements from deterministic request
    shape. LLM output may be used as advisory text elsewhere, but the harness
    does not accept model authority.
    """

    def __init__(self, repo_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "truecore_creator_security_harness",
            "authority": {
                "llm_authority": False,
                "execution_authority": False,
                "policy_authority": False,
                "mutation_authorized": False,
            },
            "laws": [
                "LLM interprets; picker chooses; policy gates; agents execute only after approval.",
                "Prompt-only production agents are forbidden.",
                "Creation tools draft contracts before activation.",
                "Harness coordinates through approved registries, not hidden imports.",
            ],
            "systems": self._system_map(),
            "agents": self._agent_catalog(),
            "workers": self._worker_catalog(),
            "capabilities": list(build_default_capability_registry().values()),
            "recipes": list(build_default_chain_recipes().values()),
            "factory_tools": factory_blueprints(),
        }

    def choose(self, request_text: str) -> dict[str, Any]:
        intent = self.classify(request_text)
        registry = build_default_capability_registry()
        capabilities = [registry[item] for item in intent.needed_capabilities if item in registry]
        recipes = [
            recipe
            for recipe in build_default_chain_recipes().values()
            if all(cap in intent.needed_capabilities for cap in recipe["capability_sequence"])
        ]
        return {
            "schema_version": 1,
            "kind": "truecore_deterministic_harness_choice",
            "request": request_text,
            "intent": intent.intent,
            "target_kind": intent.target_kind,
            "confidence": intent.confidence,
            "needed_capabilities": list(intent.needed_capabilities),
            "capability_candidates": capabilities,
            "recipe_candidates": recipes,
            "agent_candidates": self._agent_candidates(intent),
            "worker_candidates": self._worker_candidates(intent),
            "runner_executable": False,
            "llm_authority": False,
            "policy_required_before_execution": True,
            "notes": self._notes_for_intent(intent),
        }

    def answer(self, request_text: str) -> dict[str, Any]:
        choice = self.choose(request_text)
        response = self._render_choice(choice)
        return {
            "response": response,
            "metadata": {
                "harness_choice": choice,
                "source": "truecore_creator_security_harness",
            },
            "inference": {
                "model": "deterministic_truecore_harness",
                "llm_authority": False,
            },
        }

    def classify(self, request_text: str) -> HarnessIntent:
        terms = _terms(request_text)
        joined = " ".join(terms)
        creation_terms = {"create", "make", "build", "add", "draft"}
        if (
            ("harness" in terms or "chooser" in terms or "picker" in terms or "coordinate" in joined)
            and not terms.intersection(creation_terms)
        ):
            return HarnessIntent("harness_explain", "harness", ("temporal.read", "forge.relationships.trace"), 0.86)
        if "logger" in terms or "loggers" in terms or "sensor" in terms:
            return HarnessIntent("create_or_inspect_logger", "logger", ("temporal.read",), 0.82)
        if "worker" in terms or "workers" in terms:
            return HarnessIntent("create_or_inspect_worker", "worker", ("temporal.read", "forge.relationships.trace"), 0.82)
        if "agent" in terms or "agents" in terms:
            return HarnessIntent("create_or_inspect_agent", "agent", ("temporal.read", "forge.relationships.trace"), 0.84)
        if "firewall" in terms or "block" in terms or "contain" in terms:
            return HarnessIntent(
                "containment_review",
                "containment",
                ("temporal.read", "forge.relationships.trace", "central_writer.report_request", "firewall.block_ip"),
                0.86,
            )
        if "incident" in terms or "breach" in terms or "suspicious" in terms or "causality" in terms:
            return HarnessIntent(
                "investigate_security_event",
                "incident",
                ("temporal.read", "forge.relationships.trace", "central_writer.report_request"),
                0.88,
            )
        if "runtime" in terms or "health" in terms or "status" in terms or "proof" in terms or "receipt" in terms:
            return HarnessIntent("runtime_health", "runtime", ("temporal.read",), 0.8)
        if "policy" in terms or "permission" in terms or "approval" in terms:
            return HarnessIntent("policy_boundary", "policy", ("temporal.read", "central_writer.report_request"), 0.78)
        if "daily" in terms and "ledger" in terms:
            return HarnessIntent("chat_memory_status", "chat", ("temporal.read",), 0.74)
        return HarnessIntent("truecore_general", "truecore", ("temporal.read",), 0.55)

    def _system_map(self) -> dict[str, Any]:
        return {
            "core": sorted(_child_dirs(self.repo_root / "truecore")),
            "routes": sorted(path.stem for path in (self.repo_root / "truecore" / "routes").glob("*.py") if path.stem != "__init__"),
            "runtime": sorted(path.stem for path in (self.repo_root / "truecore" / "runtime").glob("*.py") if path.stem != "__init__"),
            "sensors": sorted(path.stem for path in (self.repo_root / "truecore" / "sensors").glob("*.py") if path.stem != "__init__"),
            "tools": sorted(path.stem for path in (self.repo_root / "truecore" / "tools").glob("*.py") if path.stem != "__init__"),
            "frontdoor": {
                "root": str(self.repo_root / "frontdoor"),
                "active_surface": "Rust frontdoor serving embedded HTML plus static assets",
            },
        }

    def _agent_catalog(self) -> list[dict[str, Any]]:
        root = self.repo_root / "truecore" / "live_agents" / "AGENTS" / "agents"
        rows = []
        for path in sorted(root.glob("*.agent.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {"agent_id": path.stem, "name": path.stem, "risk_tier": 5, "requires_approval": True}
            rows.append(
                {
                    "agent_id": data.get("agent_id", path.stem),
                    "name": data.get("name", path.stem),
                    "runtime_language": data.get("runtime_language", "unknown"),
                    "risk_tier": data.get("risk_tier", 0),
                    "requires_approval": bool(data.get("requires_approval")),
                    "dry_run_supported": bool(data.get("dry_run_supported")),
                    "required_params": list(data.get("required_params", [])),
                    "manifest_path": str(path),
                }
            )
        return rows

    def _worker_catalog(self) -> list[dict[str, Any]]:
        return default_worker_registry()

    def _agent_candidates(self, intent: HarnessIntent) -> list[dict[str, Any]]:
        agents = self._agent_catalog()
        if intent.target_kind in {"incident", "containment", "agent", "worker"} or "causality" in intent.intent:
            preferred = [
                row
                for row in agents
                if row["agent_id"] == "temporal_causality_log_checker"
                or (intent.target_kind == "containment" and "firewall" in row["agent_id"])
            ]
            return preferred or agents
        return agents[:2]

    def _worker_candidates(self, intent: HarnessIntent) -> list[dict[str, Any]]:
        workers = self._worker_catalog()
        if intent.target_kind in {"worker", "runtime", "incident", "truecore"}:
            return workers
        return workers[:1]

    def _notes_for_intent(self, intent: HarnessIntent) -> list[str]:
        if intent.target_kind in {"logger", "worker", "agent"}:
            return [
                f"{intent.target_kind} creation is draft-only until the authorized production route has an observed effect.",
                "Activation requires policy approval, a validated manifest/contract, and native operational receipts.",
            ]
        if intent.target_kind == "containment":
            return [
                "Firewall/block capability is high risk and approval gated.",
                "Harness may choose the capability, but cannot execute it.",
            ]
        return ["Harness output is advisory routing and contract guidance only."]

    def _render_choice(self, choice: dict[str, Any]) -> str:
        lines = [
            f"TrueCore harness classified this as `{choice['intent']}`.",
            f"Target: `{choice['target_kind']}`.",
            "Chosen capabilities: " + ", ".join(choice["needed_capabilities"]),
            "Execution: not authorized from chat.",
            "LLM authority: false.",
        ]
        if choice["notes"]:
            lines.append("Notes: " + " ".join(choice["notes"]))
        return "\n".join(lines)


def _terms(value: str) -> set[str]:
    return {term for term in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split() if term}


def _child_dirs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [item.name for item in path.iterdir() if item.is_dir() and item.name != "__pycache__"]
