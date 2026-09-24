# TrueVision candidate-agent handoff instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and
`TrueVision/transfer_to_truecore/AGENTS.md`. This directory is transfer material
for TrueCore-formatted candidate agents.

## Production entrypoint and allowed operations

No production invocation is established by these files. The handoff lists
`truevision_worker_receipt_router`, `truevision_consensus_reasoning_agent`, and
`truevision_zero_tolerance_gate_agent` as candidates for later validation and
registration by TrueCore.

## Forbidden operations and authority boundary

Do not call candidate files registered agents or invoke them through a made-up
adapter. Directory presence and manifest format do not grant activation.

## Inputs, outputs, receipts, and provenance

Keep candidate manifest identity, source hash, validation result, review status,
and any later TrueCore registration receipt distinct. A handoff report is not
an execution receipt.

## Known staged paths and next contract

`HANDOFF_REPORT.md` marks all three `promotion_ready: REVIEW` and
`contract_status: CANDIDATE`. Verify current TrueCore catalog and code before
claiming promotion.
