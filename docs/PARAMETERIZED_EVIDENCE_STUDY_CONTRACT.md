# Parameterized evidence-study contract

Status: implemented freeze/validation boundary for the TrueSystems operator.

## Purpose

A parameterized evidence study is the reusable form of the data-first workflow:

```text
data -> profile -> reversible shape -> ask the human's question
     -> agent proposes technical definitions -> human may override
     -> freeze -> compute -> claim audit -> charts/answer
```

The operator agent owns profiling, shaping, question decomposition, parameter
selection, computation orchestration, claim inspection, and communication. The
human supplies data, intent, authority, constraints, and optional overrides.

The coded boundary in
`TrueCore/truecore/agents/parameterized_study.py` validates/finalizes the plan and
emits a deterministic freeze receipt. It deliberately does not read datasets,
run statistics, select values, call arbitrary commands, or write an answer.

This is an extension of the Codex–TrueSystems operator handoff. It is not a new
AWRAG runtime and does not replace TrueMem, TrueCore, or the Evidence Workspace
Agent.

## Lifecycle states

| Phase | Meaning | Computation allowed |
| --- | --- | --- |
| `DATA_REQUESTED` | Operator has requested or located authorized data | No |
| `DATA_PROFILED` | Actual schema/ranges/statuses/missingness are recorded | No |
| `QUESTION_REQUESTED` | Shaped capability summary has been shown; human question is pending/present | No |
| `PARAMETERS_DRAFTED` | Agent has proposed technical parameters | No |
| `PARAMETERS_LOCKED` | Layers, questions, parameters, isolation, and outputs are frozen | Yes, after a valid freeze receipt |

Changing any locked parameter creates a new plan version and hash. A result must
identify the exact freeze hash under which it was computed.

## Plan schema

The top-level schema is `truesystems_parameterized_evidence_study@1`:

```json
{
  "schema": "truesystems_parameterized_evidence_study@1",
  "study_id": "stable-study-id-v1",
  "original_request": "The human's exact request",
  "phase": "PARAMETERS_LOCKED",
  "operator_identity": "codex-thread-or-operator-id",
  "data_layers": [],
  "questions": [],
  "parameters": [],
  "isolation_rules": [],
  "output_contract": {}
}
```

### Data layer

```json
{
  "layer_id": "historical_object_status",
  "source_ref": "/absolute/path/to/source.parquet",
  "source_sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "source_kind": "file",
  "observed_fields": ["object_id", "epoch_utc", "status"],
  "observed_time_range": {
    "start_utc": "2024-01-01",
    "end_utc": "2024-12-31",
    "resolution": "daily",
    "timezone_assumption": "UTC"
  },
  "authority": "source status and orbital observations; not service assignment",
  "allowed_question_ids": ["Q1"],
  "forbidden_join_layer_ids": ["current_geometry"]
}
```

`source_kind` is one of `file`, `directory`, `database`, `api`, `stream`, or
`artifact`. `observed_fields` names fields actually found, not fields hoped for.
Unknown time endpoints are `null`; they are not guessed.

### Question

```json
{
  "question_id": "Q1",
  "text": "For each object, what are the final operational and first dying dates?",
  "layer_ids": ["historical_object_status"],
  "answer_class": "MEASUREMENT",
  "required_fields": ["object_id", "epoch_utc", "status"],
  "unavailable_fields": ["official_service_withdrawal_time"],
  "status": "READY"
}
```

The implemented `answer_class` vocabulary is `MEASUREMENT`, `DESCRIPTIVE`,
`PROXY`, or `COUNTERFACTUAL`. Use `MEASUREMENT` for directly or mechanically
derived quantities and explain derivation through parameters. Never select
`MEASUREMENT` when the target is unavailable and only a substitute exists.

### Parameter

```json
{
  "parameter_id": "operational_altitude_min_km",
  "value": 460.0,
  "value_type": "number:kilometres",
  "set_by": "agent",
  "rationale": "Separates the trusted operational shell band from raising/decay observations.",
  "evidence_basis": "Profiled operational-status altitude distribution and prior source contract.",
  "affects_question_ids": ["Q1"],
  "locked": true
}
```

Agent selection is the default. The human does not need to supply technical
settings. A human override must preserve the proposal:

```json
{
  "parameter_id": "recovery_horizon_minutes",
  "value": 120,
  "value_type": "integer:minutes",
  "set_by": "human_override",
  "agent_proposed_value": 60,
  "override_reason": "Operational monitoring window is two hours.",
  "rationale": "Human policy override retained explicitly.",
  "evidence_basis": "Human operational requirement.",
  "affects_question_ids": ["Q3"],
  "locked": true
}
```

Direct `set_by: human` is invalid. This prevents the agent from offloading
technical design onto the human and prevents a human override from being
misrepresented as an agent-derived choice.

### Isolation rule

```json
{
  "rule_id": "historical-current-epoch-separation",
  "left_layer_id": "historical_object_status",
  "right_layer_id": "current_geometry",
  "rule": "FORBID_JOIN",
  "reason": "Current geometry cannot identify a historical serving object."
}
```

Questions that name both sides of `FORBID_JOIN` are rejected. A narrative may
compare separately computed summaries when it clearly states the different
epochs; that does not authorize a record-level join.

### Output contract

```json
{
  "required_artifacts": ["canonical_result.json", "analysis_table.csv"],
  "required_receipts": ["source_profile.json", "freeze.json", "run.json"],
  "timing_required": true,
  "failed_attempt_timing_required": true,
  "chart_label_rules": [
    "retain proxy in every proxy metric label",
    "retain flag in every binary-state aggregate label"
  ],
  "claim_audit_required": true
}
```

## Freeze receipt

`freeze_study_plan` returns
`truesystems_parameterized_evidence_study_freeze@1` containing:

- canonical frozen plan;
- deterministic `frozen_plan_sha256`;
- `computation_permitted: true`;
- explicit false declarations for evidence authority, relationship authority,
  and answer composition.

The same semantic JSON object produces the same hash regardless of key order or
whitespace. Array order remains meaningful.

## Required operator sequence

1. Preserve the original request.
2. Ask for or locate authorized data.
3. Hash and profile every source.
4. Build reversible analysis layers.
5. Record layer authorities and forbidden joins.
6. Tell the human what the data contains and cannot contain.
7. Ask what the human wishes to know unless already supplied.
8. Split the request into stable question/evidence obligations.
9. Select technical parameters from pre-outcome source evidence.
10. Disclose definitions and limitations.
11. Record human overrides without erasing agent proposals.
12. Validate and freeze.
13. Compute only under the returned hash.
14. Preserve timings and failures.
15. Inspect raw sibling/state-machine relationships.
16. Audit each material claim by class and evidence reference.
17. Produce exact-labeled charts and an ordinary-language answer.
18. Run external acceptance tests.

## Validation rules

The implemented validator rejects:

- missing required top-level fields;
- unknown schemas/phases;
- empty data, question, or parameter lists;
- malformed SHA-256 identities;
- duplicate layer/question/parameter/rule IDs;
- unknown layer or question references;
- self-forbidden joins;
- questions crossing forbidden joins;
- unknown answer classes/source kinds;
- parameters without rationale/evidence basis;
- direct human parameter setting that is not an explicit override;
- overrides without the agent proposal and reason;
- unlocked parameters at freeze time;
- incomplete output contracts.

## Non-authorities

A valid plan or freeze receipt does not prove:

- source correctness;
- semantic correctness of the operator's parameter choices;
- execution success;
- statistical validity;
- causal identification;
- a serving identity, failure event, user transfer, or load change;
- evidence completeness;
- permission for mutation or external action;
- correctness of final prose.

Those require source evidence, executable results, receipts, acceptance checks,
and operator claim inspection.

## Commands

```bash
cd TrueCore
PYTHONPATH=. python -m truecore.agents.parameterized_study validate /path/to/plan.json
PYTHONPATH=. python -m truecore.agents.parameterized_study freeze /path/to/plan.json \
  --output /path/to/freeze.json
```

The output write is atomic. The tool writes no dataset, mutates no source, and
executes no arbitrary analysis command.
