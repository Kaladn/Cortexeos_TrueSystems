# TrueCore/truecore/agents agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueCore/truecore/agents/`. Read `TrueCore/truecore/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

This directory mixes coded agents and bounded workers. In
`parameterized_study.py`, `validate_study_plan` and `freeze_study_plan` validate
and freeze an operator-authored plan; they do not compute its evidence.
`evidence_workspace.py:EvidenceWorkspaceAgent` is implemented, but its
tracked manifest states `IMPLEMENTED_NOT_REGISTERED` and has no runnable
command. Trace TrueCore's caller and manifest before treating any class here
as invokable.

## Local code-defined surface

- `__init__.py`.
- `base.py`: AgentDecision (line 34), Agent (line 72).
- `bounded_job_workers.py`: selected (line 18), patch_files (line 31), acceptance_run (line 96), history_readiness (line 126), and 2 more source definitions.
- `chain_auditor.py`: ChainAuditorAgent (line 20).
- `cognitive.py`: CognitiveState (line 42), CognitiveAgent (line 58).
- `containment.py`: ContainmentAdvisorAgent (line 25).
- `decoy_orchestrator.py`: DecoyStrategy (line 23), DecoyOrchestratorAgent (line 67).
- `escalation.py`: CellEscalationState (line 25), EscalationAgent (line 72).
- `evidence_workspace.py`: EvidenceWorkspaceContractError (line 46), EvidenceService (line 51), canonical_bytes (line 56), stable_hash (line 65), and 3 more source definitions.
- `machine_navigation_workers.py`: filesystem_list (line 78), filesystem_find (line 82), filesystem_read_metadata (line 86), filesystem_hash (line 90), and 11 more source definitions.
- `parameterized_study.py`: ParameterizedStudyContractError (line 34), canonical_bytes (line 38), stable_hash (line 42), validate_study_plan (line 46), and 3 more source definitions.
- `process_change.py`: ProcessChangeAgent (line 18), main (line 156).
- 4 additional direct source files; enumerate them before claiming complete coverage.

## Allowed and forbidden operations

Use only the exact callable reached through the applicable parent authority path; do not create a substitute wrapper or ingress. Do not infer inputs, effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

Registration and dead-code status are unresolved from this local inventory. Trace non-test callers and verify an actual run.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
