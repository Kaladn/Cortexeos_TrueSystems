---
doc_id: cortex_memory_architecture
title: AnchorWorks SecureCore TrueVision Memory Architecture
when_to_use: Use when discussing chat memory, L1-L4 memory layers, AW/SC/TV memory boundaries, ledger versus memory, promotion, counts, OpenAI memory limits, or what happens after chat.
---

# AnchorWorks / SecureCore Memory Architecture vNext

## Purpose

The memory system exists to separate:

```text
what happened
```

from:

```text
what the machine thinks about what happened
```

This distinction is mandatory.

A machine that cannot separate source truth from interpretation will eventually confuse observation, inference, opinion, summaries, and assumptions.

The result is memory corruption.

The purpose of the L1-L4 architecture is to prevent that corruption.

## Core Law

```text
L1 stores.
L2 references.
L3 learns.
L4 reasons.
Counts remember.
Renderers speak.
```

No layer may impersonate another layer.

## Layer 1 - Source Truth

L1 contains the immutable source record.

Examples:

```text
chat messages
operator commands
tool outputs
sensor observations
system events
receipts
```

L1 answers:

```text
What happened?
```

Not:

```text
What does it mean?
```

Properties:

```text
append-only
timestamped
source-backed
replayable
auditable
```

L1 is evidence. L1 is not memory interpretation.

## Layer 2 - Context References

L2 attaches context to L1.

Examples:

```text
citations
related messages
related documents
source references
cross-links
attachments
```

L2 answers:

```text
What is connected?
```

Not:

```text
What is true?
```

L2 creates navigation. L2 never modifies L1.

## Layer 3 - Lessons Learned

L3 stores approved observations.

Examples:

```text
operator preferences
project rules
repeated corrections
workflow discoveries
accepted lessons
```

L3 answers:

```text
What have we learned repeatedly?
```

L3 requires promotion. Nothing enters L3 automatically.

## Layer 4 - Reasoning Hooks

L4 stores reasoning scaffolds.

Examples:

```text
project hypotheses
future investigations
architectural theories
candidate explanations
research trails
```

L4 answers:

```text
What should we investigate next?
```

L4 is not truth. L4 is possibility.

## Structural Memory

L1-L4 are not the brain.

The brain is separate:

```text
counts
relationships
positional observations
approved memory structures
```

Examples:

```text
lifetime counts
phrase counts
neighbor counts
structural observations
```

The machine's long-term memory is not chat history. It is accumulated structure.

## Chat Ledger Is Not Memory

Critical law:

```text
chat ledger != memory
```

Chat ledger is:

```text
record
```

Memory is:

```text
promoted structure
```

A system that confuses the two becomes a retrieval engine instead of a memory system.

## OpenAI Relationship

OpenAI does not own memory.

OpenAI does not own truth.

OpenAI does not own promotion.

OpenAI may:

```text
help interpret
help explain
help interact
help draft
```

OpenAI may not:

```text
promote memory
rewrite counts
rewrite truth
```

OpenAI is a tutor. AnchorWorks remains authority.

## TrueVision Relationship

TrueVision does not create memory.

TrueVision witnesses state.

TrueVision records:

```text
glyph state
document state
image state
video state
surface state
```

Memory promotion remains separate. Witnessing is not remembering.

## SecureCore Relationship

SecureCore governs memory movement.

SecureCore decides:

```text
can promote
cannot promote
requires review
requires receipt
```

SecureCore is the authority path.

## Required Memory Claim Disclosure

No answer may claim memory unless it reports:

```text
L1 rows read
L2 hooks used
L3 lessons selected
L4 reasoning hooks selected
AW/count memory consulted or not consulted
OpenAI context packet id
```

## Implementation Lock

```text
chat ledger = L1 source
canonical writer = source authority / daily continuity
sidecar memory = temporary notes only, not brain
AW memory/counts = promoted durable memory
OpenAI context = selected packet, not memory
```

The fix is not:

```text
make SC remember more
```

The fix is:

```text
SC writes/guards L1
SC may attach L2-L4 mirrors
AW promotes/counts durable memory
OpenAI receives selected context packet
OpenAI never becomes memory owner
```

## Final Law

```text
L1 records.
L2 connects.
L3 learns.
L4 explores.
Counts remember.
SecureCore governs.
TrueVision witnesses.
OpenAI assists.
AnchorWorks decides.
```

Any design that violates these boundaries will eventually corrupt memory, blur truth, and reduce explainability.

Tiny law:

```text
Ledger records.
Mirror explains.
Counts remember.
OpenAI borrows.
SC governs.
```
