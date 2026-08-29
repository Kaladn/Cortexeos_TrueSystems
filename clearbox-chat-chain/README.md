# Clearbox Chat-Chain

This repository is a fresh Omarchy-native implementation of the bounded
Clearbox Chat-Chain salvage: one chat surface with durable single-model and
ordered-chain conversations, outputs, continuation, branching, and recovery.

It is not a Clearbox 2.5 port and does not contain TrueMem, retrieval,
citations, CompuCog, TrueVision, 6-1-6, training, evidence systems, or a general
tool framework.

[`docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md`](docs/CLEARBOX_CHAT_CHAIN_SALVAGE.md)
is the authoritative functional specification.

Omarchy owns host and plugin lifecycle. The backend owns authoritative
conversation state; the browser or other UI displays projections and never
owns that state.

The local server now serves the chat entry surface at `http://127.0.0.1:3219/`.
It opens one durable conversation per calendar day, shows the exact ordered
message projection, identifies every model output by its provider/model
identity, and routes Send and Continue commands back through Chat-Chain. The
surface does not create inline notes or citations.
