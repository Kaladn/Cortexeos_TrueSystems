# Linux TrueSystems

Local Linux source workspace for the cooperating TrueSystems components.

## Components

- `SecureCore/` — coded security agents and bounded capabilities.
- `TrueMachine/` — the Linux temporal cognition machine formerly discussed as CompuCog.
- `AWRAG-AWEAR/` — deterministic intake, mapped anchor prediction, retrieval, and citations.
- `LocalMemoryChat/` — the small local chat-continuation and cited-memory system.
- `clearbox-chat-chain/` — the local chat-chain service and plugin source.

Each component remains a distinct source boundary inside this umbrella repository.
No component was redesigned, merged internally, or rewritten during assembly.

## Assembly boundary

This repository contains current source working trees. It intentionally excludes:

- nested `.git` directories;
- runtime, state, and machine-local data;
- Python bytecode and test caches;
- external test logs and generated test artifacts.

The original canonical working directories remain unchanged. `SOURCES.md` records
their locations and the directory mapping used for this assembly.
