# TrueComputer agent and human operating contract

Read the repository-root `AGENTS.md`, `OPERATORS_MANUAL.md`, this file, and
`docs/CONTRACT.md` before changing or invoking TrueComputer. The narrowest rule
wins when rules overlap.

## 1. Purpose and ownership

TrueComputer is the deterministic Linux desktop action executor. It owns only:

- current compositor-state observation used to validate an action target;
- validation of one typed action request;
- delegation to one fixed Linux desktop backend;
- post-action state observation;
- an atomic, redacted action receipt.

The human owns intent and consequential authorization. The operator agent owns
interpretation, target selection, sequencing, explanation, and the decision to
request human approval. Hyprland owns compositor truth. The destination
application owns its own state. TrueComputer does not inherit authority from
TrueVision, TrueMachine, TrueCore, a study plan, a dashboard, a chat message, or
the mere fact that an executable is installed.

Never describe TrueComputer as a general autonomous computer user. The current
implementation is a bounded actuator with live preconditions.

## 2. Required interaction sequence

For every action:

1. preserve the human's requested outcome and scope;
2. inspect current desktop state;
3. identify the exact existing target window/workspace/coordinate;
4. determine whether the action is read-only, reversible, consequential, or
   privileged;
5. obtain human approval when required by the root contract or product policy;
6. create a single-action request with the observed active-window identity;
7. run `validate` and inspect the redacted plan;
8. immediately re-check context when focus or visible state may have changed;
9. run `execute` only with the explicit `--execute` interlock;
10. inspect the receipt and destination state at the strongest available layer;
11. report what ran, what was verified, and what remains unverified;
12. stop at the requested outcome.

Do not silently expand “open this” into logging in, accepting prompts, sending a
message, downloading a file, purchasing, publishing, deleting, or changing
system configuration.

## 3. Human authorization rules

Explicit human authorization is required immediately before actions involving:

- passwords, authentication prompts, account changes, or secrets;
- sending, posting, publishing, submitting, purchasing, or financial activity;
- deletion, overwrite, irreversible changes, or loss of access;
- package installation, service changes, firewall changes, or privilege;
- legal acceptance, consent dialogs, or security warnings;
- exposing private information to another person, service, or model;
- unattended loops or a material increase in action scope.

Earlier approval may cover a clearly bounded multi-step workflow, but only its
stated targets and consequences. A data-analysis approval, inspection request,
or “proceed” from an unrelated phase is not authorization for a desktop side
effect. The executor's `--execute` flag proves only deliberate invocation; it
does not prove the human approved the action.

Never type or store a password, private key, recovery code, token, cookie, or
other secret through TrueComputer. Ask the human to enter secrets locally.

## 4. Observation and targeting

- Use `truecomputer inspect` as the canonical request-time snapshot.
- Treat window address, class, and exact title as one target identity.
- Never target by title substring alone.
- Never reuse a request after focus, title, layout, monitor, or workspace state
  may have changed.
- Never infer a clickable coordinate from memory, a stale screenshot, or a
  different monitor scale.
- Coordinates are global Hyprland layout coordinates, not image pixels from an
  arbitrary transformed screenshot.
- A successful pointer move proves cursor position only. It proves no hover,
  selection, or application response.
- A successful text injection proves backend delivery completed while the same
  window remained active. It does not prove the application retained, submitted,
  interpreted, or acted on the text.
- Treat window titles as potentially sensitive metadata when retaining receipts.

TrueVision state is evidence, not action authority. If future visual grounding
is added, preserve screenshot epoch, monitor transform, scale, crop, target
confidence, and the mapping from image coordinates to global compositor
coordinates. Re-observe immediately before action.

## 5. Allowed live actions

Only actions implemented in the current request enum are live:

- `focus_window`: focus an exact existing Hyprland address;
- `switch_workspace`: switch to an exact existing workspace;
- `move_pointer`: move inside active monitor bounds;
- `type_text`: inject printable text into the exact active window.

All other actions are `NOT_IMPLEMENTED`, including click, scroll, drag, key
chord, application launch, shell command, file chooser operation, clipboard
mutation, screenshot interpretation, and accessibility-tree action. Do not
assemble an unreviewed substitute from unrelated tools and then call it a
TrueComputer action.

## 6. Request construction

- Use schema `truecomputer_action_request@1` exactly.
- Use a unique, filesystem-safe `request_id` of 1–128 ASCII letters, digits,
  hyphens, or underscores.
- Copy `expected_active_window` from the immediately preceding live snapshot.
- Include exactly one action.
- Keep typed text to the minimum needed and below 4096 characters.
- Do not include control characters or use text typing as a key-chord surrogate.
- Do not place authorization prose, reasoning, secrets, or unrelated context in
  the request.
- Store request files outside source repositories unless they are deliberate
  sanitized fixtures.
- Treat request files containing typed text as sensitive even though receipts
  redact that text.

Validation is mandatory before execution. Never edit a request between validate
and execute; the receipt binds the exact executed bytes by SHA-256.

## 7. Backend discipline

- Invoke executables with fixed argument vectors; never through a shell.
- Executable names are implementation constants, never request fields.
- Hyprland state and dispatches use `hyprctl`.
- Printable text uses `wtype`.
- Do not parse human-formatted Hyprland output when JSON exists.
- Do not add a dependency or daemon when the compositor already provides the
  operation with stronger state semantics.
- Rust is for validation, safe process boundaries, and receipts. It is not a
  reason to reimplement a maintained compositor protocol.
- Do not edit `/usr/share/omarchy/`.
- User-facing Omarchy/Hyprland configuration changes require the Omarchy skill,
  a config reload, `hyprctl configerrors`, and external acceptance.
- Do not enable `ydotoold`, alter `/dev/uinput` permissions, or install input
  software without explicit authorization and a separate system test.

## 8. Receipts and verification

A completed receipt must preserve:

- schema and request ID;
- SHA-256 of exact request bytes;
- redacted action summary;
- fixed backend identity;
- UTC start and completion timestamps;
- pre- and post-action window identities;
- backend completion status and non-sensitive output.

Typed text must never appear in a plan, stdout receipt, saved receipt, log, test
failure message, or screenshot. Retain only its character count and SHA-256.
Atomic receipt publication is mandatory. Do not claim success if receipt writing
fails, even when the desktop backend already acted; report the ambiguous partial
state explicitly.

Verification strength is action-specific:

- focus: active address equals target address;
- workspace: focused monitor reports the target workspace;
- pointer: post-action `cursorpos` equals the requested global coordinates;
- text: the expected window remained active; application-level content remains
  unverified unless independently observed.

Never upgrade backend success into proof of the user's intended application
outcome.

## 9. Failure and race handling

- On precondition mismatch, stop and inspect again. Do not weaken the expected
  window fields.
- On missing target, return failure. Do not create a workspace or choose a
  similarly named window.
- On backend failure, preserve stderr but check it for sensitive material before
  reporting or storing beyond the local receipt surface.
- On postcondition failure, report `OPERATION_FAILED` or ambiguous partial state;
  never retry automatically.
- On receipt failure after a backend action, do not repeat the action. Inspect
  current state and report that execution may have occurred without a receipt.
- Do not retry typing. Duplicate text can be consequential.
- A focus race invalidates the operation even if the requested target becomes
  active again afterward.
- Human mouse or keyboard use supersedes the agent. Stop when user activity or a
  changed target indicates takeover.

## 10. Development rules

- Keep this component dependency-light and comments short.
- Reject unknown JSON fields.
- Add a strict typed action rather than a stringly generic dispatcher.
- Every new action needs positive and negative unit tests, a redaction rule, a
  precondition, a postcondition, and an external acceptance case.
- Never add `run_command`, `exec`, `script`, arbitrary Hyprland dispatcher, or
  arbitrary `wtype` option fields.
- Keep screen observation, semantic reasoning, action execution, and receipts as
  separate layers.
- Do not add stale fallbacks for X11 to a Wayland-only contract.
- Do not add silent retries, hidden background services, or action batching.
- Do not write runtime requests, receipts, build targets, logs, screenshots, or
  generated fixtures into this repository.
- Use `CARGO_TARGET_DIR` outside the repository for all builds and tests.
- Run `cargo fmt --check`, `cargo clippy -- -D warnings`, unit tests, the external
  acceptance suite, `git diff --check`, and `git status --short`.
- Save external tests and UTC timestamped logs under
  `/home/lamercey/Documents/User System Test/repositories/linux TrueSystems/`.

## 11. Change review checklist

Before accepting a change, verify:

- the action surface did not become a generic command channel;
- no request value selects an executable or shell syntax;
- unknown fields still fail closed;
- exact active-window preconditions still apply;
- coordinates remain bounded by live monitor geometry;
- non-existing focus/workspace targets fail;
- typed content remains absent from every returned and saved artifact;
- receipts are atomic and bind exact request bytes;
- postconditions are checked without claiming application semantics;
- failures do not auto-retry;
- no system service, global config, device permission, or Omarchy source changed;
- documentation matches executable behavior;
- external acceptance proves both useful action validation and refusal paths.

## 12. Stop conditions

Stop and return a truthful status when:

- the requested action is absent from the enum;
- Hyprland or its expected JSON interface is unavailable;
- `wtype` is absent for text injection;
- the active window differs from the pinned identity;
- the target does not exist or coordinates are out of bounds;
- typed content contains control characters or exceeds its bound;
- authorization is missing for a consequential operation;
- verification cannot distinguish success from partial action;
- a secret would need to pass through the executor;
- the human takes over input;
- external acceptance fails in a way that undermines the capability.

Use `NOT_IMPLEMENTED`, `AUTHORIZATION_REQUIRED`, `PRECONDITION_FAILED`,
`OPERATION_FAILED`, or `AMBIGUOUS_PARTIAL_ACTION` as appropriate. Precision is
more important than making the desktop appear autonomous.
