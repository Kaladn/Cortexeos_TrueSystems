# Three-layer help system

Help is deterministic, read-only, and grounded in the current combined source.
It does not invoke an LLM, change system state, or claim evidence authority.

## Layers

1. `quick` returns the shortest accurate identification or routing answer.
2. `operate` adds the real command sequence or boundary rules.
3. `source` adds source locations resolved from the current files at request time.

## HTTP access

```text
GET  /api/v1/help/topics
POST /api/v1/help/query
```

Query body:

```json
{"question": "How does TrueMachine preserve a pulse?", "layer": 3}
```

## Chat access

Send a normal Chat-Chain turn through the unified API and select one seat:

```json
{
  "provider": "truesystems-help",
  "model": "source"
}
```

Valid help models are `quick`, `operate`, and `source`. The help output is stored
as an ordinary Chat-Chain model output and assistant message. The provider reads
the user's current message, selects a code-backed topic, and returns citations.

## Failure rules

- Empty questions fail.
- Unknown layer numbers fail.
- Unknown help model names fail.
- Missing cited files are reported as missing; no replacement claim is invented.
- A help answer never proves an operation ran.
