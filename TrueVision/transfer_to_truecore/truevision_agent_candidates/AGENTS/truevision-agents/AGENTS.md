# TrueVision/transfer_to_truecore/truevision_agent_candidates/AGENTS/truevision-agents agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueVision/transfer_to_truecore/truevision_agent_candidates/AGENTS/truevision-agents/`. Read `TrueVision/transfer_to_truecore/truevision_agent_candidates/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

This directory is staged transfer material. Its files do not establish a production invocation.

## Local code-defined surface

- `truevision_consensus_reasoning_agent.py`: stable_hash (line 26), load_packets (line 31), support_score (line 51), build_consensus (line 67), and 2 more source definitions.
- `truevision_worker_receipt_router.py`: stable_hash (line 16), load_json (line 21), route_receipt (line 29), write_decision (line 63), and 1 more source definitions.
- `truevision_zero_tolerance_gate_agent.py`: stable_hash (line 38), file_hash (line 43), validate_manifest (line 47), validate_catalog (line 71), and 3 more source definitions.

## Allowed and forbidden operations

Inspect candidate files; require receiving-runtime registration before claiming activation. Do not infer inputs, effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

Candidate status is not activation.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
