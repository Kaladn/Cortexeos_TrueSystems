# Repository Boundary Receipt

- Repository: `/home/lamercey/clearbox-chat-chain`
- Baseline commit: the commit containing this receipt (`git rev-parse HEAD`)
- Authoritative specification: `docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md`
- External verification: `/home/lamercey/Documents/User System Test/repositories/clearbox-chat-chain/output/baseline-final-20260825T121318Z.log`

## Responsibility audit

| Path | Responsibility / salvage requirement | Dependencies | Scope | Decision |
|---|---|---|---|---|
| `.gitignore` | Keeps generated runtime/build state out of source custody | Git | Boundary metadata only | KEEP |
| `README.md` | Declares purpose, exclusions, authority, and backend/UI custody law | Salvage spec | No implementation outside scope | KEEP |
| `pyproject.toml` | Packages and launches the selected Python runtime | Python, setuptools | Package metadata only | KEEP |
| `docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md` | Authoritative functional specification | None | Defines the allowed scope | KEEP |
| `docs/openapi.yaml` | Minimal HTTP/UI command and projection boundary | HTTP API | No generic patch or tool API | KEEP |
| `src/clearbox_chat_chain/__init__.py` | Package identity | Python | Package metadata only | KEEP |
| `src/clearbox_chat_chain/core.py` | Conversation persistence; branch topology; single and ordered generation; durable outputs; Continue; branching; projections; recovery; idempotency; revision concurrency; model adapter boundary | Python standard library, SQLite, configured OpenAI-compatible endpoint when selected | No excluded subsystem | KEEP |
| `src/clearbox_chat_chain/server.py` | Minimal HTTP command/query boundary | Python standard library, core service | No UI-owned state or general tool surface | KEEP |
| `omarchy/plugin/manifest.json` | Canonical thin Omarchy plugin declaration | Omarchy shell | Host integration only | KEEP |
| `omarchy/plugin/BarWidget.qml` | Thin API status/conversation control projection | Omarchy shell, local HTTP API, curl | Holds no conversation state | KEEP |
| `omarchy/systemd/clearbox-chat-chain.service` | Canonical Omarchy user-service lifecycle definition | systemd user manager, Python package | Host lifecycle only | KEEP/MOVED |
| `docs/REPOSITORY_BOUNDARY_RECEIPT.md` | Boundary and verification record | Git, external test library | Documentation only | KEEP |

## Custody

- Canonical implementation and deployable integration source are in this repository.
- Installed plugin files remain under `~/.config/omarchy/plugins/lamercey.clearbox-chat-chain/`.
- Installed service remains under `~/.config/systemd/user/`.
- Runtime SQLite state remains under `~/.local/state/clearbox-chat-chain/`.
- User-authored tests and outputs remain under `/home/lamercey/Documents/User System Test/repositories/clearbox-chat-chain/`.

## Verification

- 11 isolated acceptance tests: PASS.
- Live API conversation and echo turn: PASS.
- Canonical and installed plugin manifests: VALID.
- Canonical and installed plugin files: BYTE-IDENTICAL.
- Live plugin `refresh` and `status` IPC: RESOLVED.
- User service: ENABLED and ACTIVE.
- Runtime database inside repository: NONE.
- Python compilation: PASS.
- Salvage specification identity against recovered USB source: PASS.

## Exclusions

No Clearbox 2.5 bridge, AWEAR/AWRAG, retrieval, citations, CompuCog,
TrueVision, 6-1-6, training, evidence system, or general tool framework was
admitted.

## Next bounded gap

Implement the minimal chat surface that renders backend projections and sends
the already-defined commands without owning conversation or chain state.
