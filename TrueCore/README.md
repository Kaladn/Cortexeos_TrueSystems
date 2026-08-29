# TrueCore

TrueCore is a localhost-only defensive security organism. This public repo stays locked to runtime and support structures only. The active organism is still Python: substrates append immutable truth, Forge is being introduced under those substrate contracts, agents infer from truth, and the Reaper executes containment through a weighted consensus gate.

## Current Truth Lock

For current operational status, use:

```text
docs/security/TRUECORE_OPERATIONAL_TRUTH_LOCK.md
```

Older planning docs and README snapshots may preserve useful history, but code/tests plus the operational truth lock are the current authority.

## Current runtime

The callable inventory is code-derived rather than frozen here as a count. Use
`python -m truecore.cli.main status` and `python -m truecore.cli.main agents`
against a running organism. The package contains append-only substrates, Forge
storage including the pulse writer and WAL, coded agents, a localhost Flask
control plane, deterministic decoy routes, and policy-gated containment.

The current Linux port still contains Windows-named evidence signatures and
some legacy Windows implementation under non-default paths. Do not describe a
Windows firewall action as an available Linux containment mechanism unless a
live tool and receipt prove it.

## Current cut line
- Forge foundation exists on the `forge` branch as an optional dual-write storage spine
- Rust migration is planned, not active in runtime
- JSONL substrates remain the authoritative truth stores until cutover is explicitly proven
- Agents never mutate evidence
- Loggers log, agents infer

## Runtime Surface Cut Line

TrueCore is clean-core only in this repo state.

```text
ui_runtime: not_installed
chat_runtime: not_installed
memory_runtime: not_installed
local_model_runtime: not_installed
```

The current runtime backbone is:

- `truecore/help/` for static help corpus and code-index tooling
- `truecore/control/` for local control transport and runtime command handling
- `truecore/permissions/` for registry and gating
- `truecore/openai_session.py` for in-memory OpenAI API-key session handling
- `truecore/substrates/` for append-only truth

No embedded model backend is installed or planned. Future model assistance uses
operator-provided OpenAI API sessions and remains advisory unless separately
gated through TrueCore policy.

## Future Ports

UI, chat, and durable memory are reserved future ports, not active services.

```text
Surfaces may be added later.
Chat may be added later.
Memory may be added later.
None of them exist as active TrueCore runtime services today.
```

Prompt libraries remain available as selectable model guidance, but prompts are
not memory and do not create authority.

## Repo layout
- `truecore/` runtime organism
- `tests/` runtime and support tests
- `security_local/` legacy prototype retained for lineage only

## Quick start
```bash
python -m pip install -r truecore/requirements.txt
cp truecore/.env.example truecore/.env
python truecore/cli/seed_admin.py
python -m unittest discover -s tests -t . -v
python -c "import truecore.app; print('truecore app import ok')"
```

## Runtime entry points
- `python truecore\app.py` starts the localhost API/control backend on `127.0.0.1:5057`
- `frontdoor\` is API proxy infrastructure only; UI/chat runtime is not installed.
- `python truecore\cli\seed_admin.py` seeds the admin account
- `python -m unittest discover -s tests -t . -v` runs the current support suite

The Flask backend is API-only. Legacy Flask templates/static UI files are not active runtime surfaces.

## Authentication Direction
Local bootstrap may use a temporary `admin` account so the operator can enter the system and replace credentials through the controlled setup path. The bootstrap password is local runtime state, not a repo secret.

Near-term authentication work:
- local operator login first
- encrypted credential setup next
- remote access gated separately from localhost access
- targeted automated-agent login for specialized agents only
- no blanket login identity for every internal agent
- placeholder reserved for remote phone control from iPhone and Android

Remote/mobile control must not become active until transport, device identity, approval, and audit logging are explicit.

## Notes
This public repository carries runtime and support structures only. Broader design papers, migration notes, and local planning artifacts stay out of GitHub.

## Rear-Looking Snapshot
- TrueCore has been pulled out of the earlier Security Local bootstrap and re-formed as a layered organism with explicit truth, inference, control, and deception boundaries.
- The current pre-Forge runtime is live as a Python organism built around 7 substrates, 7 agents, 7 structured log streams, a consensus-gated Reaper, and a localhost-only Flask control plane.
- Truth is still carried by append-only hash-chained JSONL substrates. Agents interpret that truth but do not mutate it. The Reaper executes validated actions rather than inventing policy.
- The repo has already been narrowed on purpose: runtime and support structures are public, while broader planning papers and local design archives stay outside GitHub.
- The current shape is intentionally transitional. It is stable enough to inspect, test, and extend, but it is not yet in Forge cutover mode.

## Next Units
This section is a living execution ledger. Each item starts as a forward-looking task. When a unit is completed, rewrite the line into past tense so the README becomes its own rolling project history instead of accumulating stale plans.

- Pending: prove the public runtime cleanly with a deterministic end-to-end vertical slice, including one trap hit flowing through substrates, agents, consensus, and operator logging.
- Pending: prove Forge dual-write, WAL recovery, and writer behavior under load before treating it as a trustworthy backing layer.
- Pending: replace hot-path synchronous write pressure with a safer writer pattern so truth capture stays deterministic under stress without blocking request handling.
- Pending: wire a real HID collector behind the existing HID substrate so human-attestation signals come from hardware activity rather than synthetic records alone.
- Pending: lock logging and write-path visibility before branching the operator command center into active UI work.
- Pending: define one future operator surface only after runtime write integrity is proven.
