# Next Session Handoff

## Objective

Continue the Omarchy-native Clearbox Chat-Chain salvage without expanding its
scope. The next bounded implementation gap is the minimal chat surface that
renders backend projections and submits the already-defined commands without
owning conversation or chain state.

Do not begin TrueMem integration, retrieval, citations, CompuCog,
TrueVision, 6-1-6, training, evidence systems, or a general tool framework.

## Repository

- Path: `/home/lamercey/clearbox-chat-chain`
- Branch: `main`
- Proven baseline commit: `7f9d082dfb45a84414a0356fad3b5959bf262309`
- Authoritative specification: `docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md`
- Boundary receipt: `docs/REPOSITORY_BOUNDARY_RECEIPT.md`

Read the authoritative specification and boundary receipt before changing
implementation.

## Current repository custody

- Backend/API source: `src/clearbox_chat_chain/`
- HTTP contract: `docs/openapi.yaml`
- Canonical Omarchy plugin source: `omarchy/plugin/`
- Canonical user-service definition: `omarchy/systemd/`
- Installed plugin: `~/.config/omarchy/plugins/lamercey.clearbox-chat-chain/`
- Installed user service: `~/.config/systemd/user/clearbox-chat-chain.service`
- Runtime database: `~/.local/state/clearbox-chat-chain/chat-chain.sqlite3`
- External tests and output: `/home/lamercey/Documents/User System Test/repositories/clearbox-chat-chain/`

Runtime state, installed configuration, user-authored tests, and test artifacts
must remain outside the repository.

## Proven state

At the baseline checkpoint:

- 11/11 isolated acceptance tests passed.
- Live API conversation creation and echo execution passed.
- User service was enabled and active.
- Canonical and installed plugin files were byte-identical.
- Canonical and installed plugin manifests validated.
- Live plugin `refresh` and `status` IPC resolved after restarting the Omarchy shell.
- No SQLite runtime state existed inside the repository.
- The authoritative specification matched the recovered USB copy exactly.

Primary verification artifact:

`/home/lamercey/Documents/User System Test/repositories/clearbox-chat-chain/output/baseline-final-20260825T121318Z.log`

## Codex access for the next session

Global Codex configuration now contains:

```toml
sandbox_mode = "danger-full-access"
approval_policy = "on-request"
```

This setting activates only when a new Codex session starts. It grants full
command filesystem/network access while retaining on-request approvals.

Configuration acceptance artifact:

`/home/lamercey/Documents/User System Test/system/output/codex-access-policy-20260825T122129Z.log`

## Required next-session opening checks

1. Confirm the new session reports `danger-full-access` and `on-request`.
2. Confirm `git -C /home/lamercey/clearbox-chat-chain status --short --branch` is clean.
3. Read `docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md` and `docs/REPOSITORY_BOUNDARY_RECEIPT.md`.
4. Confirm the user service is enabled and active.
5. Run the existing external acceptance suite before changing behavior if the baseline cannot otherwise be trusted.

## Next bounded task

Design and implement only the minimal chat surface described by the salvage
specification:

- conversation list;
- selected branch projection and branch path;
- user and assistant messages;
- every stable model output with Continue action;
- branch action from an earlier message;
- composer;
- single/chain mode and ordered model seats;
- send and cancellation commands;
- reload entirely from backend projections.

The UI may retain only unsent draft text, theme, dimensions, and scroll
position. It must not own conversation, branch, turn, chain, output, checkpoint,
or active execution state.

Stop and challenge any proposed file that does not serve a salvage
responsibility or thin Omarchy host integration.
