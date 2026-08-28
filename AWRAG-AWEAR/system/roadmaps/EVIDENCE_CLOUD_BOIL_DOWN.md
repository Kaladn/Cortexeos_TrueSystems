# Evidence Cloud Boil-Down

Status: active dirty-repo tool lane; not default query behavior.

Purpose:

```text
existing query packet
-> admitted top-K evidence blocks
-> temporary in-memory evidence cloud
-> temporary local count field
-> re-ask the same question inside that cloud
-> one proved boil-down step
-> operator decides stop, continue, widen, or reject
```

This is not autonomous answer generation.

It is operator-stepped evidence tightening.

## Law

```text
Pull evidence first.
Build the local evidence cloud second.
Recount only that admitted cloud.
Re-ask the question inside that cloud.
Show the answer before the next step.
Operator decides the next squeeze.
```

Short form:

```text
Each step must prove itself before the next step runs.
```

## Why This Exists

Normal query already finds evidence and receipts.

Evidence Cloud Boil-Down asks a different question:

```text
Given only the evidence AW already admitted,
what answer zone wins when that small evidence packet is treated
as its own temporary count field?
```

That moves beyond "here are the receipts" without letting speech come from the void.

## CLI

Default operator-stepped run:

```powershell
python -m awear.cli evidence-speech --packet <query-output.json> --out <speech-output-folder>
```

Optional question override:

```powershell
python -m awear.cli evidence-speech --packet <query-output.json> --question "same or corrected question" --out <speech-output-folder>
```

Explicit auto-pass test mode:

```powershell
python -m awear.cli evidence-speech --packet <query-output.json> --out <speech-output-folder> --max-passes 3 --auto-passes
```

`--auto-passes` is off by default.

## Outputs

```text
EVIDENCE_CLOUD_SPEECH_SUMMARY.json
EVIDENCE_CLOUD_SPEECH_SUMMARY.md
per_case/<case_id>_evidence_cloud_speech.json
per_case/<case_id>_evidence_cloud_speech.md
evidence_trace/<case_id>_evidence_cloud_trace.json
pretty_answer/<case_id>_pretty_answer.json
pretty_answer/<case_id>_pretty_answer.md
receipts/run_receipt.json
receipts/inputs_receipt.json
receipts/no_mutation_receipt.json
```

The evidence trace is authority.

The pretty answer is the operator view.

## One-Step Default

By default the command runs one proved pass.

The trace records:

```text
pass number
input block count
sentence zone count
winning zone
winning anchors
support score
support level
micro-map summary
step_proved=true
changed_from_previous
drift_flag
next_action_required
```

The next action is always an operator decision:

```text
stop
continue
widen
reject
```

## Boundaries

This lane does not:

```text
run dataset retrieval
run native topK again
run intake
change ranking
change counts
write dataset state
train anything
call a model
search outside the packet
walk full documents
```

It reads only:

```text
answer_packet.locations
```

from an existing query packet.

## Relationship To Other Speech Lanes

`packet-speech`:

```text
existing packet
-> document-only readable answer / refusal
```

`count-walk-speech`:

```text
query
-> count-selected block
-> block-anchor local spine
-> rough anchor walk
```

`evidence-speech`:

```text
existing packet
-> temporary evidence cloud
-> local micro-count field
-> one proved boil-down answer zone
```

## Success Condition

A successful run proves:

```text
the packet was not mutated
no dataset files were mutated
no retrieval/intake/model work ran
the local evidence cloud was built in memory
the question was re-asked inside that cloud
one answer zone was selected
citations remain attached
the next step requires operator choice
```

## Failure / Refusal

If the packet has no admitted evidence blocks, the tool must return:

```text
support_level=insufficient
citations=[]
no_mutation_receipt
```

It must not invent an answer.
