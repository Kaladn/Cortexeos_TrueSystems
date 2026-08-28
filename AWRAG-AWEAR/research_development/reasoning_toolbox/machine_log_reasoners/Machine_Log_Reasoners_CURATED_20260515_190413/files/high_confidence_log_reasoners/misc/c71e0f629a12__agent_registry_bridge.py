#!/usr/bin/env python3
"""
Agent Registry Bridge

Real code:  CSV loading, contract validation, safety gating, operator/agent/engine separation
Pseudocode: SecureCore registration, runtime dispatch, agent lifecycle (marked with PSEUDO:)

This file is the bridge between the extraction pipeline (this machine)
and SecureCore (your other machine). Load the CSVs, validate, and
hand off to your registry.

Drop this next to your securecore_agents.csv and agent_catalog.csv.
"""

import csv
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================================
# ENUMS — real code
# ============================================================================

class AgentTier(Enum):
    OPERATOR = "operator"       # tools — atomic, no autonomy
    AGENT = "standalone"        # goal-driven, selects tools
    ENGINE = "engine"           # reasoning substrate, feeds agents


class DestructionLevel(Enum):
    SAFE = 0        # pure logic
    LOW = 1         # read-only
    MODERATE = 2    # network/external
    ELEVATED = 3    # write/modify — needs confirmation
    HIGH = 4        # delete/overwrite — needs sandbox
    CRITICAL = 5    # irreversible — manual only


class PromotionGate(Enum):
    CLEAR = "YES"
    REVIEW = "REVIEW"
    BLOCKED = "NO"


# ============================================================================
# DATA STRUCTURES — real code
# ============================================================================

@dataclass
class OperatorContract:
    """The contract a tool/agent/engine carries."""
    input_shape: str
    output_shape: str
    assumptions_in: str
    assumptions_out: str
    side_effects: str
    dependencies: str
    statefulness: str
    sync_mode: str
    failure_modes: str = ""


@dataclass
class SafetyProfile:
    """Destruction scoring and runtime safety gates."""
    destruction_score: int
    risk_type: str
    risk_reason: str
    requires_confirmation: bool
    sandbox_required: bool


@dataclass
class RegisteredOperator:
    """A fully validated, registry-ready operator/agent/engine."""
    operator_id: str
    name: str
    category: str
    tier: AgentTier
    definition: str
    source_file: str
    contract: OperatorContract
    safety: SafetyProfile
    promotion: PromotionGate
    contract_status: str
    confidence: str


# ============================================================================
# CSV LOADER — real code
# ============================================================================

class CatalogLoader:
    """
    Loads agent_catalog.csv or securecore_agents.csv into
    structured RegisteredOperator objects.
    """

    TIER_MAP = {
        "standalone": AgentTier.AGENT,
        "operator": AgentTier.OPERATOR,
    }

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.operators: Dict[str, RegisteredOperator] = {}
        self.by_category: Dict[str, List[RegisteredOperator]] = {}
        self.by_tier: Dict[AgentTier, List[RegisteredOperator]] = {
            AgentTier.OPERATOR: [],
            AgentTier.AGENT: [],
            AgentTier.ENGINE: [],
        }

    def load(self) -> int:
        """Load CSV and return count of operators loaded."""
        with open(self.csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                op = self._row_to_operator(row)
                if op:
                    self.operators[op.operator_id] = op

                    # Index by category
                    if op.category not in self.by_category:
                        self.by_category[op.category] = []
                    self.by_category[op.category].append(op)

                    # Index by tier
                    self.by_tier[op.tier].append(op)

        return len(self.operators)

    def _row_to_operator(self, row: dict) -> Optional[RegisteredOperator]:
        """Convert a CSV row to a RegisteredOperator."""
        try:
            # Determine tier — engines are agents that act as reasoning substrates
            raw_tier = row.get("agent_tier", "operator")
            cat = row.get("category", "")

            if cat == "engines":
                tier = AgentTier.ENGINE
            else:
                tier = self.TIER_MAP.get(raw_tier, AgentTier.OPERATOR)

            dscore = int(row.get("destruction_score", "0"))

            contract = OperatorContract(
                input_shape=row.get("input_shape", "UNKNOWN"),
                output_shape=row.get("output_shape", "UNKNOWN"),
                assumptions_in=row.get("assumptions_in", "UNKNOWN"),
                assumptions_out=row.get("assumptions_out", "UNKNOWN"),
                side_effects=row.get("side_effects", "UNKNOWN"),
                dependencies=row.get("dependencies", "UNKNOWN"),
                statefulness=row.get("statefulness", "UNKNOWN"),
                sync_mode=row.get("sync_mode", "UNKNOWN"),
            )

            safety = SafetyProfile(
                destruction_score=dscore,
                risk_type=row.get("risk_type", "none"),
                risk_reason=row.get("risk_reason", ""),
                requires_confirmation=row.get("requires_confirmation", "NO") == "YES",
                sandbox_required=row.get("sandbox_required", "NO") == "YES",
            )

            promo_raw = row.get("promotion_ready", "NO")
            promotion = PromotionGate(promo_raw) if promo_raw in ("YES", "REVIEW", "NO") else PromotionGate.BLOCKED

            return RegisteredOperator(
                operator_id=row.get("operator_id", ""),
                name=row.get("name", ""),
                category=cat,
                tier=tier,
                definition=row.get("definition", ""),
                source_file=row.get("source_file", ""),
                contract=contract,
                safety=safety,
                promotion=promotion,
                contract_status=row.get("contract_status", "UNKNOWN"),
                confidence=row.get("category_confidence", "LOW"),
            )
        except Exception:
            return None

    def get(self, operator_id: str) -> Optional[RegisteredOperator]:
        """Look up operator by ID."""
        return self.operators.get(operator_id)

    def find_by_name(self, name: str) -> List[RegisteredOperator]:
        """Find operators by name (partial match)."""
        name_lower = name.lower()
        return [op for op in self.operators.values() if name_lower in op.name.lower()]

    def get_safe_operators(self, max_score: int = 2) -> List[RegisteredOperator]:
        """Get operators at or below a destruction score threshold."""
        return [op for op in self.operators.values()
                if op.safety.destruction_score <= max_score]

    def get_tools(self) -> List[RegisteredOperator]:
        """Get all operator-tier items (tools)."""
        return self.by_tier[AgentTier.OPERATOR]

    def get_agents(self) -> List[RegisteredOperator]:
        """Get all agent-tier items."""
        return self.by_tier[AgentTier.AGENT]

    def get_engines(self) -> List[RegisteredOperator]:
        """Get all engine-tier items."""
        return self.by_tier[AgentTier.ENGINE]

    def stats(self) -> dict:
        """Return summary statistics."""
        scores = [op.safety.destruction_score for op in self.operators.values()]
        return {
            "total": len(self.operators),
            "tools": len(self.by_tier[AgentTier.OPERATOR]),
            "agents": len(self.by_tier[AgentTier.AGENT]),
            "engines": len(self.by_tier[AgentTier.ENGINE]),
            "categories": len(self.by_category),
            "avg_destruction": sum(scores) / len(scores) if scores else 0,
            "needs_confirmation": sum(1 for op in self.operators.values()
                                      if op.safety.requires_confirmation),
            "needs_sandbox": sum(1 for op in self.operators.values()
                                 if op.safety.sandbox_required),
        }


# ============================================================================
# SAFETY GATE — real code
# ============================================================================

class SafetyGate:
    """
    Runtime safety enforcement. Sits between the registry and execution.

    TOOLS DO WORK
    AGENTS DECIDE WORK
    ENGINES DEFINE REALITY
    """

    def can_execute(self, op: RegisteredOperator) -> Tuple[bool, str]:
        """Check if an operator can execute without additional gates."""
        if op.safety.sandbox_required:
            return False, f"BLOCKED: sandbox required (score={op.safety.destruction_score})"
        if op.promotion == PromotionGate.BLOCKED:
            return False, "BLOCKED: not promoted"
        if op.safety.requires_confirmation:
            return False, f"NEEDS_CONFIRMATION: score={op.safety.destruction_score}"
        return True, "CLEAR"

    def can_chain(self, op_a: RegisteredOperator, op_b: RegisteredOperator) -> Tuple[bool, str]:
        """
        Check if operator A can feed into operator B.
        Real type+semantics compatibility check.
        """
        a_out = op_a.contract.output_shape
        b_in = op_b.contract.input_shape

        # Both unknown = can't verify
        if a_out == "UNKNOWN" or b_in == "UNKNOWN":
            return False, "UNKNOWN: cannot verify compatibility"

        # Destruction escalation check
        combined_score = max(op_a.safety.destruction_score, op_b.safety.destruction_score)
        if combined_score >= 4:
            return False, f"BLOCKED: chain destruction score {combined_score} >= 4"

        # PSEUDO: In production, do deeper type/semantic matching:
        #   if not securecore.type_engine.is_compatible(a_out, b_in):
        #       shim = securecore.shim_registry.find_shim(a_out, b_in)
        #       if shim:
        #           return True, f"SHIM_REQUIRED: {shim.name}"
        #       return False, "INCOMPATIBLE: output/input mismatch"

        return True, "COMPATIBLE"

    def approve_execution(self, op: RegisteredOperator, approver: str = "system") -> bool:
        """
        PSEUDO: Human-in-the-loop confirmation for elevated operations.

        In production:
            # confirmation = securecore.approval_queue.request(
            #     operator_id=op.operator_id,
            #     risk_type=op.safety.risk_type,
            #     risk_reason=op.safety.risk_reason,
            #     requested_by=approver,
            # )
            # return confirmation.approved
        """
        return False  # Default deny until confirmed


# ============================================================================
# AGENT REGISTRY — pseudocode integration to SecureCore
# ============================================================================

class AgentRegistry:
    """
    PSEUDO: This is where you wire into SecureCore's actual registry.

    The CatalogLoader + SafetyGate are real and portable.
    This class shows how they connect to your runtime.
    """

    def __init__(self, catalog_path: str):
        self.loader = CatalogLoader(catalog_path)
        self.gate = SafetyGate()
        self._registered: Dict[str, RegisteredOperator] = {}

    def initialize(self):
        """Load catalog and register all cleared operators."""
        count = self.loader.load()
        print(f"Loaded {count} operators from catalog")

        registered = 0
        blocked = 0
        confirmation_queue = 0

        for op_id, op in self.loader.operators.items():
            can_run, reason = self.gate.can_execute(op)

            if can_run:
                self._register(op)
                registered += 1
            elif "NEEDS_CONFIRMATION" in reason:
                # PSEUDO: Queue for human approval
                # securecore.approval_queue.add(op)
                confirmation_queue += 1
            else:
                blocked += 1

        print(f"Registered: {registered}")
        print(f"Awaiting confirmation: {confirmation_queue}")
        print(f"Blocked: {blocked}")

    def _register(self, op: RegisteredOperator):
        """
        PSEUDO: Register operator in SecureCore's runtime.

        In production:
            # agent_def = {
            #     "id": op.operator_id,
            #     "name": op.name,
            #     "category": op.category,
            #     "entry_point": op.name,  # function to call
            #     "source": op.source_file,
            #     "definition": op.definition,
            #     "risk": {
            #         "score": op.safety.destruction_score,
            #         "type": op.safety.risk_type,
            #         "confirmation": op.safety.requires_confirmation,
            #         "sandbox": op.safety.sandbox_required,
            #     },
            #     "contract": {
            #         "input": op.contract.input_shape,
            #         "output": op.contract.output_shape,
            #         "assumptions_in": op.contract.assumptions_in,
            #         "assumptions_out": op.contract.assumptions_out,
            #         "side_effects": op.contract.side_effects,
            #         "statefulness": op.contract.statefulness,
            #         "sync_mode": op.contract.sync_mode,
            #     },
            # }
            # securecore.registry.register(agent_def)
            # securecore.capability_index.add(op.operator_id, op.contract)
        """
        self._registered[op.operator_id] = op

    def get_tools_for_agent(self, agent_id: str, max_destruction: int = 2) -> List[RegisteredOperator]:
        """
        Get tools an agent is allowed to use, filtered by safety.

        PSEUDO: In production:
            # allowed = securecore.policy_engine.get_allowed_tools(
            #     agent_id=agent_id,
            #     max_destruction=max_destruction,
            #     context=securecore.current_context,
            # )
            # return [self.loader.get(t) for t in allowed]
        """
        return [op for op in self._registered.values()
                if op.tier == AgentTier.OPERATOR
                and op.safety.destruction_score <= max_destruction]

    def build_agent_chain(self, steps: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate a proposed chain of operator IDs.
        Returns (valid, list of reasons/issues).

        PSEUDO: In production:
            # return securecore.chain_validator.validate(steps)
        """
        issues = []
        for i in range(len(steps) - 1):
            op_a = self._registered.get(steps[i])
            op_b = self._registered.get(steps[i + 1])

            if not op_a:
                issues.append(f"MISSING: {steps[i]} not registered")
                continue
            if not op_b:
                issues.append(f"MISSING: {steps[i + 1]} not registered")
                continue

            can_chain, reason = self.gate.can_chain(op_a, op_b)
            if not can_chain:
                issues.append(f"{op_a.name} -> {op_b.name}: {reason}")

        valid = len(issues) == 0
        return valid, issues

    def request_elevated_execution(self, operator_id: str, reason: str) -> bool:
        """
        PSEUDO: Request execution of a confirmation-required operator.

        In production:
            # ticket = securecore.approval_queue.create_ticket(
            #     operator_id=operator_id,
            #     reason=reason,
            #     requested_by=securecore.current_agent,
            #     risk_profile=self.loader.get(operator_id).safety,
            # )
            # return ticket.wait_for_approval(timeout=300)
        """
        op = self._registered.get(operator_id) or self.loader.get(operator_id)
        if not op:
            return False
        print(f"[APPROVAL REQUIRED] {op.name} (score={op.safety.destruction_score}, "
              f"risk={op.safety.risk_type}): {reason}")
        return False  # Default deny

    def export_for_securecore(self, output_path: str):
        """
        Export registered operators as JSON for SecureCore ingestion.

        PSEUDO: In production, SecureCore pulls from this or from GitHub:
            # securecore.sync_agent.pull_catalog(
            #     source="github://your-repo/contract_extraction/securecore_agents.csv",
            #     # OR
            #     source=output_path,
            #     validate=True,
            #     dry_run=False,
            # )
        """
        import json
        agents = []
        for op in self._registered.values():
            agents.append({
                "id": op.operator_id,
                "name": op.name,
                "category": op.category,
                "tier": op.tier.value,
                "entry_point": op.name,
                "definition": op.definition,
                "source_file": op.source_file,
                "risk": {
                    "score": op.safety.destruction_score,
                    "type": op.safety.risk_type,
                    "reason": op.safety.risk_reason,
                    "confirmation": op.safety.requires_confirmation,
                    "sandbox": op.safety.sandbox_required,
                },
                "contract": {
                    "input": op.contract.input_shape,
                    "output": op.contract.output_shape,
                    "assumptions_in": op.contract.assumptions_in,
                    "assumptions_out": op.contract.assumptions_out,
                    "side_effects": op.contract.side_effects,
                    "dependencies": op.contract.dependencies,
                    "statefulness": op.contract.statefulness,
                    "sync_mode": op.contract.sync_mode,
                },
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"agents": agents, "count": len(agents)}, f, indent=2)

        print(f"Exported {len(agents)} agents to {output_path}")


# ============================================================================
# TOOLMAKER GATE — real code + pseudocode
# ============================================================================

class ToolmakerGate:
    """
    Gate between Toolmaker (bot that creates new tools) and the registry.
    Nothing enters the system without passing contracts + safety.

    Rule: Toolmaker -> Contract Agent -> Safety Gate -> Registry
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def submit_new_tool(self, name: str, source_file: str,
                        input_shape: str, output_shape: str,
                        side_effects: str, definition: str) -> Tuple[bool, str]:
        """
        Validate and register a tool created by the Toolmaker bot.
        Returns (accepted, reason).
        """
        # Step 1: Contract must exist
        if not definition or definition.strip() == "":
            return False, "REJECTED: no definition provided (Rule 1: no raw function without definition)"

        if not input_shape or input_shape == "UNKNOWN":
            return False, "REJECTED: input_shape unknown (Rule 5: unknown assumptions = review required)"

        if not output_shape or output_shape == "UNKNOWN":
            return False, "REJECTED: output_shape unknown"

        # Step 2: Score destruction
        # PSEUDO: In production, run the full scoring engine:
        #   score = securecore.destruction_scorer.score(source_file, name, side_effects)
        #
        # For now, simple heuristic:
        score = 0
        se_lower = side_effects.lower()
        if "disk" in se_lower:
            score += 2
        if "network" in se_lower:
            score += 2
        if "db" in se_lower:
            score += 2
        if "subprocess" in se_lower:
            score += 3
        if "mutation" in se_lower:
            score += 1
        score = min(score, 5)

        if score >= 4:
            return False, f"REJECTED: destruction score {score} too high for auto-registration"

        # Step 3: Build contract
        contract = OperatorContract(
            input_shape=input_shape,
            output_shape=output_shape,
            assumptions_in="toolmaker_generated",
            assumptions_out="toolmaker_generated",
            side_effects=side_effects,
            dependencies="unknown",
            statefulness="UNKNOWN",
            sync_mode="SYNC",
        )

        safety = SafetyProfile(
            destruction_score=score,
            risk_type="unknown",
            risk_reason="toolmaker_generated",
            requires_confirmation=score >= 3,
            sandbox_required=score >= 4,
        )

        # Step 4: Register
        import hashlib
        h = hashlib.sha256(f"{source_file}|{name}|{definition}".encode()).hexdigest()[:8]
        op_id = f"toolmaker_{name}_{h}"

        op = RegisteredOperator(
            operator_id=op_id,
            name=name,
            category="toolmaker_generated",
            tier=AgentTier.OPERATOR,
            definition=definition,
            source_file=source_file,
            contract=contract,
            safety=safety,
            promotion=PromotionGate.REVIEW,  # Toolmaker output always starts as REVIEW
            contract_status="PARTIAL",
            confidence="MEDIUM",
        )

        self.registry._registered[op_id] = op
        return True, f"ACCEPTED: {op_id} (score={score}, status=REVIEW)"


# ============================================================================
# DEMO — real code showing the full flow
# ============================================================================

if __name__ == "__main__":
    import sys

    catalog = os.path.join(os.path.dirname(__file__), "securecore_agents.csv")
    if not os.path.exists(catalog):
        print(f"Catalog not found: {catalog}")
        sys.exit(1)

    print("=" * 60)
    print("Agent Registry Bridge — Demo")
    print("=" * 60)
    print()

    # Load catalog
    registry = AgentRegistry(catalog)
    registry.initialize()

    print()
    stats = registry.loader.stats()
    print(f"Stats: {stats}")

    print()
    print("--- Tier Breakdown ---")
    print(f"  Tools (operators):  {stats['tools']}")
    print(f"  Agents (standalone): {stats['agents']}")
    print(f"  Engines (substrate): {stats['engines']}")

    print()
    print("--- Safe Tools (score 0-1) ---")
    safe = registry.loader.get_safe_operators(max_score=1)
    print(f"  {len(safe)} tools available at score <= 1")

    print()
    print("--- Sample: first 5 engines ---")
    engines = registry.loader.get_engines()[:5]
    for e in engines:
        print(f"  {e.operator_id}: {e.name} (score={e.safety.destruction_score})")

    print()
    print("--- Toolmaker Gate Test ---")
    tm = ToolmakerGate(registry)

    # Good tool
    ok, reason = tm.submit_new_tool(
        name="log_line_parser",
        source_file="tools/log_parser.py",
        input_shape="raw_line:str",
        output_shape="parsed:dict",
        side_effects="none",
        definition="Parses a raw syslog line into structured fields.",
    )
    print(f"  Submit log_line_parser: {ok} — {reason}")

    # Dangerous tool
    ok, reason = tm.submit_new_tool(
        name="nuke_database",
        source_file="tools/db_ops.py",
        input_shape="db_name:str",
        output_shape="status:bool",
        side_effects="db|subprocess|disk",
        definition="Drops all tables in a database.",
    )
    print(f"  Submit nuke_database: {ok} — {reason}")

    # No definition
    ok, reason = tm.submit_new_tool(
        name="mystery_func",
        source_file="tools/unknown.py",
        input_shape="data:Any",
        output_shape="result:Any",
        side_effects="none",
        definition="",
    )
    print(f"  Submit mystery_func: {ok} — {reason}")

    # Export demo
    print()
    export_path = os.path.join(os.path.dirname(__file__), "securecore_export.json")
    registry.export_for_securecore(export_path)

    print()
    print("Done.")
