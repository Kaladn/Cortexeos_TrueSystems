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
