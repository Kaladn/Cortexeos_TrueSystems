# TrueComputer operational contract

## Authority

TrueComputer executes a caller-authored bounded action. It does not decide what
the human wants, infer permission, authenticate approval, locate a visual target,
or claim that an application accepted the resulting input. The operator retains
those responsibilities. `--execute` is an accident-prevention interlock, not
cryptographic proof of human approval.

## Backends

- Hyprland JSON IPC is the observation authority and handles focus, workspace,
  and pointer movement.
- `wtype` handles printable text through Wayland's virtual-keyboard protocol.
- Programs are invoked as fixed argument vectors. No request field becomes a
  shell command, executable name, URL, environment assignment, or output path.

## Request

```json
{
  "schema": "truecomputer_action_request@1",
  "request_id": "operator-selected-id",
  "expected_active_window": {
    "address": "0x1234",
    "class": "application-class",
    "title": "Exact current title"
  },
  "action": {"kind": "move_pointer", "x": 100, "y": 100}
}
```

Exactly one action is permitted:

- `focus_window`: exact existing `address`;
- `switch_workspace`: exact existing workspace name or numeric ID using only
  ASCII letters, digits, hyphens, or underscores;
- `move_pointer`: absolute coordinates inside an active monitor rectangle;
- `type_text`: 1–4096 printable, non-control Unicode characters.

Every request pins the full active-window identity observed immediately before
execution. This prevents a stale request from typing into or acting from a newly
focused window. Focus and workspace targets must already exist; the tool cannot
create them.

## Commands

```bash
truecomputer inspect
truecomputer validate request.json
truecomputer execute request.json --receipt-dir /approved/local/path --execute
```

`validate` performs no desktop action. `execute` re-reads live state, validates,
executes one action, observes live state again, checks the available
postcondition, and atomically renames a receipt to `<request_id>.json`.

Typed content is never copied into plans or receipts. Only its UTF-8 SHA-256 and
Unicode character count are retained. Window titles are retained because they
are part of the exact target precondition and audit record; callers must store
receipts accordingly.

## Receipt and verification states

Receipt schema `truecomputer_action_receipt@2` separates:

- `execution.status`: whether the backend was not started, failed, or executed;
- `verification.status`: whether an action-specific postcondition was verified,
  failed, not verified, or the action executed but its outcome remains
  unverified;
- top-level `status`: the combined operational state.

The combined states are:

| `status` | Meaning |
| --- | --- |
| `execution_not_started` | The backend process could not be started. |
| `execution_failed` | The backend returned nonzero; the requested action is not claimed. |
| `executed_verification_failed` | The backend returned zero, but the observable postcondition failed. |
| `executed_outcome_unverified` | The backend ran, but the intended application outcome was not observed. |
| `completed_verified` | The action-specific postcondition was directly observed. |

Text injection is always `executed_outcome_unverified` in this version. A zero
`wtype` exit and an unchanged active window verify only the delivery context.
They do not prove that the application retained, interpreted, submitted, or
acted on the text. Its nested `verification.status` is therefore
`executed_but_outcome_unverified`.

A receipt proves that an attempt record was published. Receipt existence alone
does not prove execution, verification, application success, or completion of
the human's requested outcome. Backend failures and failed postconditions must
also produce receipts after the action boundary has been entered.

## Not implemented

- arbitrary command or application execution;
- clicks, mouse buttons, scrolling, drag-and-drop, or key chords;
- screenshots, OCR, visual grounding, accessibility-tree inspection;
- password, secret, payment, publication, deletion, or confirmation workflows;
- action batching, retries, background loops, or unattended autonomy;
- proof that visible application state changed as intended.

These absences are security boundaries, not implicit permission to substitute
another tool. A later action must have a strict schema, target precondition,
backend-specific postcondition, receipt redaction rule, and external acceptance
test before it becomes live.
