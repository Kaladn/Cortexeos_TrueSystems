# TrueMachine agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

This file governs `TrueMachine/`; read the repository-root `AGENTS.md` and
narrower source-directory instructions. This legacy TrueMachine package
implements part of CompuCog's temporal machine observation: WAL durability,
Fusion Pack publication, and state verification. Broader CompuCog cognition,
lineage, and security findings must be proved from their own code paths;
the package name does not establish that coverage.

## Production entrypoints and allowed operations

`src/truemachine/cli.py:main` dispatches the component CLI. Read that parser
and the called functions before using `run` or `verify`. The repository-map
worker is a separate registered TrueCore invocation path; its successful graph
build does not authorize arbitrary TrueMachine commands.

## Forbidden operations and authority boundary

An observed pulse or security finding is not human authorization. Do not make
CompuCog or this TrueMachine package a general router, permission authority,
or action executor. Do not infer system-level admission from a direct CLI
example. Trace the actual caller through SecureCore.

## Inputs, outputs, receipts, and provenance

Preserve state directory, pulse time, source schemas, WAL state, Fusion Pack
identity, verification result, and hashes where returned. Frame/media clocks
are owned by their components. `docs/CONTRACT.md` describes the state contract;
check code and observed runtime state for the selected path.

## Known staged paths and next contract

Do not infer that every repository-map view is implemented from its catalog
name; inspect `src/truemachine/repository_views.py` and the returned status.
Read the narrower `TrueMachine/src/truemachine/AGENTS.md` before editing runtime code.
