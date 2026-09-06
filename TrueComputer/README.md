# TrueComputer

TrueComputer is the bounded Linux desktop action layer for the TrueSystems
operator. It observes Hyprland directly and delegates narrow actions to
Hyprland IPC or `wtype`. It is not a shell, autonomous planner, screen reader,
or source of human authorization.

The first slice supports:

- inspecting windows, monitors, workspaces, cursor position, and active window;
- focusing an existing window by exact Hyprland address;
- switching to an existing workspace;
- moving the pointer inside an active monitor;
- typing printable text into an exactly preconditioned active window;
- validating without action and writing an atomic redacted execution receipt.

Build and inspect:

```bash
CARGO_TARGET_DIR=/tmp/truecomputer-target cargo build --release
/tmp/truecomputer-target/release/truecomputer inspect
```

See `docs/CONTRACT.md` for request schemas and safety boundaries. Computer use
is incomplete without an operator-selected target and scope. Clicking, arbitrary
program launch, shell commands, screenshots, and vision-based target selection
are deliberately `NOT_IMPLEMENTED` in this checkpoint.
