# SecureCore Tomorrow Continuation Plan

- Created: 2026-05-16
- Purpose: restart clean after the long AW/SC alignment session
- Scope: backend only

## Start Law

```text
AnchorWorks speaks.
SecureCore guards.
Communicast carries.
The user rules.
```

Do not restart by inventing. Restart by verifying the live lane.

## First 15 Minutes

1. Check git status in SecureCore.
2. Check git status in AnchorWorks.
3. Verify AnchorWorks backend is reachable on `127.0.0.1:8081`.
4. Run the focused SecureCore checks:

```powershell
python -m unittest tests.communicast.test_contracts -q
python -m unittest tests.route_tap.test_anchorworks_route_tap tests.route_tap.test_anchorworks_client -q
python -m unittest tests.central.test_contracts tests.central.test_writer_runtime -q
```

5. Run one live AW route tap:

```text
What is Newton's first law of motion?
```

Expected shape:

```text
AW produces the face/speech.
SC may inspect route pressure.
SC does not replace AW speech.
```

## Tomorrow Work Order

### 1. SecureCore Toolbox Lock

Goal: make SC a callable AW toolbox without becoming the face.

Tasks:

- Review `SECURECORE_AW_TOOLBOX_FINALIZATION_MAP.md`.
- Confirm Communicast contract boundaries.
- Add only missing receipts/tests if the live usage path exposes gaps.
- Do not build UI.

Done when:

```text
SC toolbox messages can target AW.
SC face-claim attempts are rejected.
Every handoff has evidence_refs and trace_refs.
```

### 2. Logging Health

Goal: let SC keep us safe while AW rendering work continues.

Tasks:

- Check active loggers.
- Confirm Forge writer health.
- Confirm readers are not noisy or wasteful.
- Keep low-level watchers cheap.
- No high-tier agent runs unless anomaly or operator request triggers it.

Done when:

```text
SC can observe quietly.
Normal activity is logged within budget.
Anomalies can wake smarter agents later.
```

### 3. AW Rendering Follow-Up

Goal: continue tightening AW speech only after SC guard/toolbox lane is stable.

Tasks:

- Keep AW as the face.
- Verify Top-K/count walk is live.
- Check glue-word behavior in answer assembly.
- Confirm renderer is not dumping raw top-K labels.
- Use document facts only to tune or ground, not to replace count-walk speech.

Done when:

```text
AW answers from admitted count paths.
SC supports, logs, and protects.
No system swaps roles.
```

## Parked Until Later

```text
UI
media generation
large model tuning
new ingestion
old code imports
legacy bridge work
graph engine binding
phone control
remote control
```

## Hard No-Drift Rules

```text
No SecureCore face.
No UI work.
No god bridge.
No old system resurrection.
No prompt-only production agents.
No direct action outside Policy Gate.
No report outside Central Writer.
No support system speaks as AnchorWorks.
```

## Resume Prompt

```text
Read SECURECORE_TOMORROW_CONTINUATION_PLAN.md.
Verify AW and SC status.
Run the focused tests.
Do not touch UI.
Continue from the SecureCore toolbox lock.
```

Tiny law:

```text
Verify first.
Then build.
Then prove.
```
