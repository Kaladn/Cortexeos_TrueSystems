# TruePlug source-ancestor custody snapshot

Status: `RESEARCH_REFERENCE_NOT_RUNTIME`

This directory preserves the current filesystem state of the detached
`ClearboxPluginRunner`, two historical Forest mapper variants, two historical
Forest tokenizer variants, and the generated TruePlug build specification.
It is deliberately outside every TrueSystems component.

Nothing here is registered with TrueCore, exposed through the control API, or
accepted as an executable TrueSystems capability. The copied runner is a
same-process development host and is not a security sandbox. Its plugin code
must not be run against the live system.

## Contents

- `ClearboxPluginRunner/`: copied working-state source ancestor. Generated
  Python bytecode and test caches were excluded.
- `historical_html/`: one byte-distinct copy of each mapper/tokenizer variant.
  Each selected file also existed as a byte-identical duplicate on the other
  AWRAG data drive.
- `design_inputs/`: the downloaded build specification and the preserved tail
  conversation that identified it. These are design evidence, not executable
  authority.
- `provenance/`: source state, byte hashes, and verification material.

The source CompuCog working tree was not removed or modified. “Move into the
repo” was implemented as a verified import because the source tree contains
valuable uncommitted user work. Removing that source would have been
destructive and unnecessary.

## Authority boundary

The only valid use of this directory is read-only archaeology or copying a
specific item into a separately isolated experiment. A future TruePlug may
produce candidates for TrueCore review, but this runner itself must never be
connected to or used by TrueSystems.
