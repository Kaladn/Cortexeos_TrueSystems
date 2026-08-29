# Linux TrueSystems agent instructions

Read `OPERATORS_MANUAL.md` before operating any component.

This repository is a collection of cooperating systems, not one merged runtime.
Use the narrowest existing callable that satisfies the request. Do not invent a
bridge, agent, UI, authority layer, capture mechanism, or model behavior.

## Authority order

1. Executable code and passing tests for the exact path being claimed.
2. `OPERATORS_MANUAL.md`.
3. A component's current contract or operational-truth document.
4. Historical reports and research, which are evidence only and never runtime.

## Operating laws

- TrueVision Intake/DocuFilm is the sole document and glyph intake authority.
- TrueAudio owns audio-state logging/replay; TrueSpeech consumes replayable
  audio state for bounded speech-region and candidate-alignment outputs.
- TrueMem is deterministic mapping, retrieval, prediction-walk, and
  citation machinery. It is not an LLM and must not be given model authority.
- TrueMachine observes Linux state and writes temporal Fusion Packs. Preserve
  its WAL, pulse, timestamp, atomic-publication, and verification contracts.
- TrueCore consumes evidence and runs coded defensive agents and bounded
  capabilities. A manifest or catalog row is not proof that an agent exists.
- LocalMemoryChat produces cited local-memory packets. A renderer may speak
  from a packet, but it does not become the memory authority.
- Clearbox Chat-Chain owns durable conversation ordering and continuation.
- The control API delegates. It does not own component business logic.
- Research under `research_reference_not_runtime/` is not callable runtime.
- Never claim an operation ran without its actual return value or receipt.
- Never change implementation merely to make a test or expected outcome pass.

If documentation conflicts with code, stop using that documentation, add the
claim to `SUSPECT_DOCUMENTATION.md`, and verify the code path directly.
