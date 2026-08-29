# TrueMem Recognition + Evidence System — Direction Document

## Purpose

This document defines the intended direction of the retrieval/evidence system that will eventually connect to the Clearbox Chat-Chain surface.

It is **directional architecture only**.

Do not implement this system from this document.

Do not invent missing algorithms.

Do not infer that old Clearbox, CortexOS, LakeSpeak, or other historical architectures must be recreated.

Exact implementation laws, binary formats, symbol widths, ranking rules, intake rules, and source contracts will be supplied separately.

The immediate goal is simply to preserve where this system is going and why.

---

# 1. Core idea

We are not primarily building “AI memory.”

We are building **recognition and evidence recovery**.

The system must preserve source reality in a form that allows a machine to recognize previously encountered concepts, identities, positions, neighborhoods, and relationships, then recover the exact evidence associated with them.

Conceptually:

```text
source data
→ structured intake
→ lexicon
→ stable dataset-local symbols
→ counts
→ positions
→ relationships
→ binary retrieval structures
→ recognition
→ exact evidence recovery
```

The AI model does not need to remember everything.

The system needs to know:

```text
what existed
where it existed
when it existed
what lived near it
what related to it
and how to recover the exact source
```

---

# 2. TrueMem / TrueMem role

TrueMem means:

```text
AnchorWorks Evidence Aware Retrieval
```

TrueMem means:

```text
AnchorWorks RAG
```

For now, treat TrueMem as the same general retrieval/evidence family unless a later specification explicitly separates them.

The important point is that this is **not ordinary vector RAG**.

The retrieval engine is intended to operate from deterministic symbolic structure such as:

```text
lexicon identity
symbol identity
occurrence counts
source positions
co-occurrence
neighborhoods
relationships
source coordinates
```

A model may reason over the returned evidence.

The retrieval system itself does not need to pretend to be a reasoning model.

---

# 3. Chat surface as the common working surface

The Clearbox Chat-Chain salvage is intended to become the common conversation surface.

Eventually the interaction should look approximately like:

```text
HUMAN
  ↓
CODEX / CHATGPT
  ↓
TrueMem QUERY
  ↓
TrueMem EVIDENCE OUTPUT
  ↓
CODEX / CHATGPT
  ↓
FINAL ANSWER FROM THE PROVIDED EVIDENCE
```

All of this should appear in the **same chat history**.

There should not be a separate citation panel that forces the user to hunt down where evidence came from.

The evidence itself should appear chronologically in the conversation.

Example:

```text
USER:
What were the final settings we used for the i9-13900 with the Hyper 212 EVO?

CODEX:
I need retrieval against the historical dataset.

TrueMem:
Relevant evidence found.

Source:
...

Exact passage:
...

Coordinates:
...

CODEX:
Based on that evidence, the preserved settings were...
```

The retrieval output remains independently visible.

The model's interpretation does not replace the source evidence.

---

# 4. The chat surface does not own TrueMem

Chat-Chain and TrueMem are separate systems.

Chat-Chain eventually needs only enough abstraction to allow an external system to participate in a chain:

```text
participant receives declared input
→ participant performs its own work
→ participant returns durable output
→ output appears in chat history
→ next participant may consume it
```

Chat-Chain must not implement TrueMem internally.

TrueMem must not require Chat-Chain to know its internal retrieval algorithms.

---

# 5. Exact source is the authority

Original admitted source must remain recoverable.

The long-term system must not depend on summaries as factual memory.

Source preservation concept:

```text
RAW SOURCE = authority
SUMMARY = convenience
SYMBOLIC STRUCTURE = recognition / retrieval machinery
MODEL ANSWER = interpretation
```

Never invert this hierarchy.

A model answer is not source truth.

A summary is not source truth.

---

# 6. Initial source class: chats

The first major recognition dataset will be conversation history.

The local chat surface should eventually capture everything that passes through it regardless of provider.

We do not want separate memories such as:

```text
OpenAI memory
Codex memory
Anthropic memory
local-model memory
```

The conversation belongs to the local system.

Producer/provider identity is metadata.

Example conceptual record:

```text
message
    source = local chat surface
    producer = human | codex | chatgpt | truemem | other
    provider = openai | local | other
    timestamp
    branch
    turn
    exact content
```

Anything seen by the chat surface may later become eligible for intake.

---

# 7. Daily append model

New chat material should eventually be admitted on a daily basis.

Daily append is preferred over repeatedly rebuilding the entire historical dataset.

Conceptually:

```text
today's completed chat
→ determine what is not yet admitted
→ preserve exact source
→ structural intake
→ lexicon new identities
→ assign symbols
→ update counts
→ update positions
→ update relationships
→ append binary structures
→ produce intake receipt
```

This is append-oriented.

Exact immutability and binary update laws will be specified later.

---

# 8. Lexicon

Each dataset has a lexicon that tells the system what symbolic identities are known in that dataset.

One important property is the ability to perform a cheap recognition pre-check.

Conceptually:

```text
query term / Anchor
→ check dataset lexicon

if absent:
    dataset does not know this Anchor
    no valid retrieval path exists for it
    stop or report absence

if present:
    resolve symbol
    continue retrieval
```

This prevents wasting computation searching a dataset for identities it does not contain.

Exact lexicon law will be supplied later.

---

# 9. Symbolizer

Intake assigns stable dataset-local symbolic identities.

The symbol is an address/identity used by the machine.

The symbol does **not** replace the original source.

Conceptually:

```text
source text
    "i9-13900"

dataset-local identity
    Anchor X

binary symbolic structures
    X occurs at these positions
    X has these counts
    X has these neighbors
    X has these relationships
```

The exact fixed-width symbol format will be defined separately.

Do not invent it from this document.

---

# 10. Structural source coordinates

Text intake should preserve structural identity.

At minimum, the future system is expected to distinguish concepts such as:

```text
dataset
source
block
sentence
object
```

Each admitted unit should have stable identity/coordinates appropriate to its role.

The purpose is not merely to know that a word occurred.

It must be possible to recover:

```text
which source
which block
which sentence
which object
where inside the source
```

Exact formatting will be specified later.

---

# 11. Counts, positions, neighborhoods, and relationships

The durable symbolic layer is concerned with structural recognition.

A useful simplification is:

```text
who lived where
when
next to whom
and in what relationship
```

The system will eventually retain information such as:

```text
occurrence counts
positions
neighborhood relationships
co-occurrence
source adjacency
object relationships
temporal relationships when applicable
```

Retrieval can then recognize combinations that uniquely identify old evidence.

Example:

```text
i9-13900
+
Hyper 212 EVO
```

Either term may appear many times independently.

Their shared neighborhood may identify the one historical conversation containing the desired settings.

---

# 12. Recognition, not summary recall

A key conceptual law:

```text
the system does not need to "remember" the old conversation
```

Instead:

```text
query arrives
→ query Anchors are recognized
→ their previous locations are recognized
→ shared neighborhoods and relationships are evaluated
→ exact source evidence is recovered
```

This is why this system should be described primarily as **recognition + evidence recovery**, not model memory.

---

# 13. Agent continuity summaries

Daily summaries still have a purpose, but not as factual source memory.

They exist primarily for **agent continuity and working relationship continuity**.

A daily agent summary should emphasize things such as:

```text
what working behavior changed
what the human corrected in the agent
what the agent corrected in the human
what assumptions were rejected
what interaction patterns worked well
what caused repeated friction
what engineering direction changed
what unfinished work remains
```

The goal is not:

```text
"Today we discussed X, Y, and Z."
```

The goal is closer to:

```text
"This is how the human and agent learned to work together today."
```

These summaries should not replace the original chats.

---

# 14. Summary accumulation

Daily summaries should be preserved individually.

Do not create an endless destructive chain of:

```text
daily summary
→ weekly summary
→ monthly summary
→ summary of summary
→ original behavioral detail disappears
```

The individual daily summaries remain available.

Later they may themselves be ingested into the recognition/6-1-6 system.

This creates the possibility of recognizing recurring behavioral patterns across time.

Example:

```text
Day 1:
agent expanded scope
human corrected scope

Day 4:
agent expanded scope
human corrected scope

Day 7:
same pattern

Day 10:
same pattern
```

If a pattern becomes persistent, it may justify promotion into a harder standing instruction such as an `AGENTS.md` rule.

The purpose is not punishment.

It is gradual discovery of a stable human-machine working relationship.

---

# 15. Multimodal dataset intake

The system will eventually operate on more than text.

Sources may contain:

```text
text
tables
charts
graphs
images
audio
video
```

Investigation requires the system to preserve relationships between these objects and the surrounding source.

A graph on page 12 is not an unrelated attachment if the surrounding text discusses that graph.

The system should know that they occupy the same evidence neighborhood.

---

# 16. Object identity

Non-text source objects should receive stable source-local or dataset-local object identity.

Conceptually:

```text
OBJECT-0001
type = chart
source = document A
page = 12

related:
    block 44
    block 45

position:
    between block 44 and block 45
```

Binary recognition structures do not need to permanently store enormous derived visual representations.

They need enough identity, coordinates, relationships, and extracted evidence to recover the original object.

---

# 17. Charts, graphs, and tables must be understood as data

Intake cannot merely record:

```text
"there is a chart here"
```

If a chart contains meaningful data, that data is part of the evidence.

Example:

```text
chart object

title:
Quarterly Revenue

series:
Q1 = ...
Q2 = ...
Q3 = ...
Q4 = ...

units:
USD
```

The extracted values, labels, axes, legends, annotations, and meaningful relationships should be recoverable.

The surrounding text and the chart data remain related.

This allows later investigation such as:

```text
text claims X
chart demonstrates Y
```

and gives the model enough evidence to compare them.

---

# 18. Video intake

Video must receive object identity and source coordinates.

Video transcript is important evidence.

At minimum, future video intake should preserve:

```text
video object identity
source
transcript
transcript timestamps
relevant source relationships
important visual/data objects discovered inside the video
```

If a video contains a chart or other information-bearing visual object, that object may itself require structured intake.

---

# 19. TrueVision's future role

TrueVision may eventually assist multimodal intake.

Its role is to observe and extract source state when ordinary text extraction is insufficient.

Important conceptual distinction:

```text
TrueVision intake logs
!=
permanent recognition memory
```

TrueVision may generate substantial intermediate observational state.

Most of that state does not need to live permanently in the final symbolic count/relation files.

The durable system needs the meaningful identities, positions, relationships, extracted data, and source recovery information.

A useful mental model:

```text
TrueVision = microscope
source/object store = specimen
TrueMem symbolic layer = recognition/index structure
```

Exact TrueVision integration is future work.

Do not implement it now.

---

# 20. Evidence returned to AI

When retrieval succeeds, the model should receive a bounded evidence packet.

Exact schema will be designed later, but directionally it should contain information such as:

```text
evidence identity
dataset identity
source identity
source coordinates
exact source text
related object identity when applicable
object data when applicable
retrieval relationship
provenance / hashes / receipt information
```

The model constructs its answer from that evidence.

Material claims about the private dataset should be grounded in supplied evidence rather than invented from model memory.

---

# 21. Negative recognition matters

TrueMem should be comfortable reporting absence.

Examples:

```text
Anchor not present in dataset lexicon.

Available evidence does not establish this.

Relevant source object exists but has not been structurally interpreted yet.

Retrieval found related material but not enough evidence to answer confidently.
```

Missing evidence must remain missing.

Do not manufacture evidence to satisfy the question.

---

# 22. CPU-first retrieval

The recognition/retrieval system is expected to be predominantly CPU/storage oriented.

The GPU is not required merely to perform symbolic retrieval.

GPU use may occur elsewhere for:

```text
local inference
future 6-1-6 model experiments
TrueVision processing
other specialized workloads
```

Do not couple ordinary evidence retrieval to GPU availability.

---

# 23. What we are explicitly not doing now

This direction document does **not** authorize implementation of:

```text
TrueMem
lexicon
symbol allocator
binary format
ranking algorithm
relationship algorithm
multimodal intake
TrueVision integration
6-1-6 training
agent-summary generation
long-term recognition store
evidence packet schema
```

Those will be specified and implemented incrementally.

Current work remains focused on establishing the Chat-Chain backend foundation.

---

# 24. Intended build progression

Current intended order is approximately:

```text
1. Chat-Chain backend and durable conversation surface

2. Make ChatGPT/Codex usable through or visible through the common surface

3. Persist exact local daily conversation history

4. Define text intake law

5. Define lexicon law

6. Define symbolization and binary structures

7. Build minimal chat recognition/retrieval

8. Return exact evidence through Chat-Chain

9. Let Codex/ChatGPT synthesize answers from that evidence

10. Add daily agent-continuity summaries

11. Later add structured non-text objects

12. Later connect TrueVision intake where needed
```

This order may change as evidence from implementation changes.

Do not treat it as an irreversible migration schedule.

---

# 25. Final system philosophy

The long-term system should remain understandable.

```text
Preserve source reality.

Give things stable identities.

Know where they occurred.

Know what lived around them.

Know how they relate.

Recognize them when they appear again.

Recover the exact evidence.

Let the AI reason from the evidence.
```

We are not trying to make the model magically remember everything.

We are giving the machine an evidence-backed recognition system so it can reliably find what it has seen before.

That is the direction.

---

## Codex instruction

Preserve this document as future-system context.

Do not begin implementing it.

Do not expand the current Chat-Chain task because of anything described here.

When later work reaches one of these boundaries, inspect the authoritative specifications supplied at that time rather than inventing missing details from this direction document.
