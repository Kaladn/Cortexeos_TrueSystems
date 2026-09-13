Yes. Now that the repository map exists, **we should define exactly what we expect this graph to expose before Codex keeps adding graph machinery**.

The graph should not become a generic “code relevance graph.” It should become a **structural investigation surface** with independently preserved relationship channels. Security, orphaned code, dead paths, undocumented behavior, ownership, testing, provenance, drift, and impact analysis are different views over the same source-grounded graph.

The current baseline is already the right starting point:

> **ownership — source order — dependency**

with exact name-access evidence underneath it, while explicitly *not* pretending source order is control flow. 

And Codex already proposed exactly the right philosophical rule for weighting: keep byte distance, line distance, ownership depth, call hops, test witnesses, etc. as **separate channels**, not one mushy relevance score. 

# 1. The graph's primary job

Every graph result should ultimately answer some variation of:

**What is this?**  
**Who owns it?**  
**What touches it?**  
**What does it touch?**  
**How is it reached?**  
**What depends on it?**  
**What evidence proves those relationships?**  
**What appears disconnected, weakly connected, contradictory, stale, or improperly connected?**

And every answer should terminate in exact source locations.

The graph itself never becomes source authority.

```text
GRAPH CLAIM
    ↓
relationship witness
    ↓
object identity
    ↓
path + byte span
    ↓
source hash
    ↓
EXACT SOURCE
```

---

# 2. Core graph node types

I would keep these explicit rather than representing everything as generic `NODE`.

### Repository-level

```text
repository
revision
package/component
directory
module/file
```

### Code structure

```text
class/type
function
method
constructor
scope
basic block
statement
expression
identifier occurrence
parameter
return
exception site
constant
configuration key
entrypoint
```

### Runtime/security objects later

```text
process
service
socket
network endpoint
filesystem object
agent
tool
capability
human
device
session
dataset
canonical evidence object
```

The static repository mapper shouldn't pretend to know the runtime objects yet. But its schema should leave room for them.

---

# 3. Ownership relationships

These answer **who structurally owns what**.

```text
CONTAINS
OWNED_BY
DECLARES
DEFINED_IN
MEMBER_OF
NESTED_IN
HAS_PARAMETER
HAS_RETURN
HAS_EXCEPTION_PATH
HAS_ENTRYPOINT
```

This is your custody channel.

It prevents this:

```text
same file
+ same name
= same ownership
```

That is forbidden.

Codex already captured this law: a relationship cannot cross function/module ownership without an explicit edge, and same file/same name cannot establish ownership. 

---

# 4. Dependency relationships

These tell us **what relies on what**.

```text
IMPORTS
IMPORTED_BY
CALLS
CALLED_BY
REFERENCES
REFERENCED_BY
INSTANTIATES
INHERITS
IMPLEMENTS
REGISTERS
CONFIGURES
USES_SCHEMA
USES_CONSTANT
LOADS_RESOURCE
TEST_TARGETS
ENTRYPOINT_TO
```

These are already extremely useful for security.

Example:

```text
external route
→ handler
→ helper
→ filesystem writer
```

Even before authoritative control flow exists, that dependency chain tells us where to investigate.

---

# 5. Source-order relationships

These are purely positional.

```text
PREVIOUS_SIBLING
NEXT_SIBLING
SOURCE_BEFORE
SOURCE_AFTER
BYTE_DISTANCE
LINE_DISTANCE
ORDINAL_DISTANCE
```

These must remain explicitly weaker than ownership or dependency relationships.

Proximity means:

> **look here**

not:

> **this owns / causes / executes this**

That's exactly the same law as your text retrieval work.

---

# 6. Future control-flow graph

This is the big missing axis.

Eventually we want real parser/compiler-derived:

```text
FLOWS_TO
BRANCH_TRUE
BRANCH_FALSE
LOOP_BACK
BREAK_TO
CONTINUE_TO
RETURNS_TO
RAISES_TO
EXCEPTION_HANDLER
CALLS_TO
```

But **only when qualified by a real structural authority**.

No heuristic “line 91 probably runs before line 97.”

Until this is proven, the current middle axis stays:

**SOURCE ORDER.**

---

# 7. Future data-flow graph

Separate again.

```text
DEFINES_VALUE
READS_VALUE
WRITES_VALUE
PRODUCES_VALUE
CONSUMES_VALUE
BINDS_ARGUMENT
RETURNS_VALUE
PASSES_VALUE_TO
MUTATES_OBJECT
READS_STATE
WRITES_STATE
TAINT_SOURCE
TAINT_SINK
SANITIZES
```

This becomes extraordinarily important for security.

Example:

```text
network payload
→ parser result
→ variable
→ agent prompt
→ tool argument
→ shell command
```

Now we're talking.

---

# 8. Relationship resolution status

Every edge needs honesty.

Keep the proposed states:

```text
WITNESSED_STATIC
WITNESSED_RUNTIME
UNIQUE_RESOLUTION
CANDIDATE
AMBIGUOUS
EXTERNAL
DYNAMIC
UNRESOLVED
SYNTAX_UNAVAILABLE
```



I would add only where genuinely needed:

```text
INFERRED_POSITIONAL
DECLARED_CONFIGURATION
GENERATED_CODE
```

But those must remain separate from witnessed static/runtime relationships.

---

# 9. The weights — do NOT create one magic score

This is critical.

I do **not** want:

```text
security_relevance = 0.82
```

That eventually becomes arbitrary bullshit.

Instead every relationship carries measurable channels.

## Structural distance

```text
ownership_depth
dependency_hops
call_graph_hops
import_graph_hops
source_line_delta
source_byte_delta
sibling_ordinal_delta
```

## Witness mass

```text
static_occurrence_count
runtime_witness_count
test_witness_count
configuration_witness_count
```

## Source/revision state

```text
revision_distance
last_changed_generation
source_hash_match
parser_status
```

## Future execution

```text
control_flow_hops
data_flow_hops
runtime_execution_count
```

## Security

```text
authority_boundary_crossings
privilege_transition_count
external_input_distance
protected_sink_distance
authentication_gate_count
validation_gate_count
```

Again: **raw measurements.**

---

# 10. Positional pressure

The formula Codex suggested is useful:

```text
pressure(distance) =
    (N - distance + 1) / N
```

But pressure means:

> traversal priority

It does **not** mean:

```text
truth
ownership
execution probability
security risk
```



I would retain:

```text
raw distance
radius
numerator
denominator
axis
direction
```

So every weighting is reconstructable.

---

# 11. Parent scores

Here's where your parent-child design becomes useful.

We can produce parent summaries from **observed children**, without inventing hand weights.

For a module:

```text
module
├── 107 functions
├── 84 called
├── 23 never called
├── 59 tested
├── 48 untested
├── 3 external entrypoints
├── 4 privileged writes
└── 2 unresolved security-sensitive dependencies
```

The module's surface doesn't say:

> “Security score = 71.”

It reports measured child state.

If some UI later needs ranking, rank using explicit tuples, not hidden weighting.

Example:

```text
(
  unresolved_privileged_paths,
  untested_privileged_paths,
  external_entrypoints,
  orphan_children,
  total_children
)
```

That's deterministic.

---

# 12. Security graph view

This is probably the most valuable new view.

We identify objects by security role:

```text
EXTERNAL_SOURCE
PARSER
VALIDATOR
AUTHENTICATOR
AGENT_INPUT
AGENT
CAPABILITY_GATE
TOOL
PROCESS_EXECUTOR
NETWORK_SINK
FILESYSTEM_WRITER
PROTECTED_OBJECT
CANONICAL_EVIDENCE
PRIVILEGED_CONFIG
SECRET_STORE
```

Then inspect paths.

Example:

```text
EXTERNAL_SOURCE
      ↓
   parser
      ↓
 model context
      ↓
    tool
      ↓
 filesystem writer
      ↓
 protected config
```

Question:

> **Where is the authority gate?**

If none exists between low-authority input and high-authority mutation:

**boundary investigation target.**

Not automatically a vulnerability.

An investigation target.

---

# 13. Boundary elevation

One particularly useful relationship:

```text
LOWER_AUTHORITY
→
HIGHER_AUTHORITY
```

Examples:

```text
network → filesystem
document → shell
model text → tool execution
plugin result → privileged action
ordinary user → root operation
unregistered device → human-presence witness
```

Then graph:

```text
authority_before
authority_after
gate_present?
gate_type?
gate_source?
```

That becomes one of TrueCog's killer inspections.

---

# 14. Security boundary weakness classes

I'd expose these as derived conditions.

### Ungated elevation

Low-authority source reaches higher-authority sink without an explicit gate.

### Gate bypass

There is a normal guarded path and another path around it.

### Inconsistent enforcement

Two equivalent entrypoints apply different security checks.

### Stale authorization

Capability remains valid after the state/session that authorized it ended.

### Direct subsystem bypass

Example:

```text
model → TrueMem
```

when policy requires:

```text
model → TrueCore → TrueMem
```

### Provenance bypass

Derived data enters an authoritative path without source identity/hash.

### Mutable-to-canonical leak

Working/generated output reaches canonical evidence storage improperly.

---

# 15. Orphaned code

Now we get into cleanup/archaeology.

An orphan is **not merely “zero callers.”**

There are legitimate zero-caller objects:

```text
CLI entrypoints
callbacks
framework hooks
reflection targets
plugins
tests
dynamic imports
registration surfaces
external APIs
```

So orphan detection should be evidence-based.

Candidate orphan:

```text
defined
AND
no resolved callers
AND
no registrations
AND
no entrypoint relationship
AND
no test target
AND
no configuration reference
AND
no runtime witness
```

Then status:

```text
ORPHAN_CANDIDATE
```

Never immediately `DEAD_CODE`.

---

# 16. Strong orphan

Higher confidence:

```text
no callers
no reverse references
no imports
no registrations
no tests
no runtime witnesses
no documentation references
not exported
not framework hook
```

That becomes:

```text
STRONG_ORPHAN_CANDIDATE
```

Still requires review before deletion.

---

# 17. Dead code

Dead code differs from orphan code.

Example:

```python
return x
do_something()
```

`do_something()` has an owner and may have references elsewhere, but this occurrence is unreachable.

Future control-flow analysis can identify:

```text
UNREACHABLE_BLOCK
UNREACHABLE_STATEMENT
CONSTANT_FALSE_BRANCH
POST_RETURN_CODE
POST_RAISE_CODE
```

That requires real CFG authority.

Don't fake it today.

---

# 18. Abandoned subsystem detection

This is a parent-level orphan.

Suppose:

```text
package X
├── 61 files
├── 430 functions
└── no incoming dependency from active runtime
```

The entire package may be archaeological.

That's much more useful than finding one unused function at a time.

Potential status:

```text
DETACHED_SUBGRAPH
```

Then inspect whether it's:

```text
historical
test-only
prototype
deprecated
future
truly abandoned
```

---

# 19. Duplicate implementations

Graphing can also expose:

```text
same or near-identical function names
same dependency surfaces
same ownership pattern
same output schema
different locations
```

But don't infer duplicate semantics from names alone.

Good candidates:

```text
DUPLICATE_IMPLEMENTATION_CANDIDATE
PARALLEL_GENERATION
LEGACY_IMPLEMENTATION
```

Then inspect exact source.

---

# 20. Split-brain architecture

Very relevant to TrueSystems archaeology.

Example:

```text
TrueMachine A
TrueMachine B
```

Both may implement overlapping roles.

Graph asks:

```text
Which one has incoming runtime edges?
Which one is called by TrueCore?
Which one is referenced by docs?
Which one has tests?
Which one is detached?
```

This exposes **live authority vs historical lineage**.

---

# 21. Documentation drift

Huge one.

Create relationships:

```text
DOC_MENTIONS
DOC_CLAIMS_METHOD
DOC_CLAIMS_ROUTE
DOC_CLAIMS_FORMAT
```

against actual code.

Then find:

```text
document claims feature
BUT
no implementation relationship exists
```

or:

```text
code exposes feature
BUT
documentation has no reference
```

You just watched Codex manually discover exactly this in TrueCog.

Eventually graph it.

---

# 22. Test coverage relationships

Not line coverage first.

Relationship coverage.

```text
TEST_TARGETS
TEST_CALLS
TEST_IMPORTS
RUNTIME_TEST_WITNESS
```

Then ask:

> Which privileged code has no tests?

Much more meaningful than generic percentage coverage.

Example:

```text
filesystem writer
incoming edges: 12
tests: 0
```

That's interesting.

---

# 23. Untested security paths

Derived query:

```text
external entrypoint
→ ...
→ privileged sink
```

Does any admitted test witness the path?

If not:

```text
SECURITY_PATH_UNTESTED
```

Again, not necessarily broken.

But worth attention.

---

# 24. Error-path analysis

Eventually CFG lets us map:

```text
TRY
CATCH
RAISE
RETURN_ERROR
FAIL_OPEN
FAIL_CLOSED
```

We want especially:

```text
verification fails
→ what happens?
```

Does it:

```text
STOP
```

or:

```text
continue anyway
```

Today's frozen-file event demonstrated **fail closed**.

Graphing failure paths could find where that isn't true.

---

# 25. Mutation graph

Track every code surface capable of changing state:

```text
WRITES_FILE
DELETES_FILE
RENAMES_FILE
CHMOD
CHOWN
SPAWNS_PROCESS
MODIFIES_CONFIG
WRITES_DATABASE
NETWORK_SEND
```

Then map incoming callers.

Question:

> Who can reach mutation?

This gives you the **machine's writable attack surface**.

---

# 26. Canonical-evidence adjacency

For every canonical evidence store:

```text
who can read?
who can write?
who can rename?
who can delete?
who can generate adjacent files?
who verifies hash?
who consumes the results?
```

Any write-capable path should stand out.

The ideal canonical node eventually looks like:

```text
READERS: many
DERIVERS: many
WRITERS: admission system only
IN-PLACE MUTATORS: zero
```

---

# 27. Sensitive sink graph

Tag sinks such as:

```text
shell execution
sudo/root escalation
filesystem mutation
credential access
network egress
model/tool invocation
system shutdown
package install
service control
firewall mutation
canonical evidence admission
```

Then query backward:

> What reaches this?

This is incredibly valuable.

---

# 28. External-input graph

Similarly tag sources:

```text
HTTP input
webpage
email
plugin result
uploaded document
camera
microphone
USB
network socket
clipboard
model output
user input
```

Then query forward:

> Where can this flow?

Once real data-flow exists, security gets dramatically stronger.

---

# 29. Prompt-injection paths

Eventually:

```text
external document
→ parsed text
→ model context
→ tool selection
→ privileged capability
```

The graph should explicitly show whether there is a:

```text
HUMAN_AUTHORITY_GATE
```

between semantic influence and execution.

That is one of the central TrueCog security questions.

---

# 30. Provenance weakness

Find derived objects with no recoverable source relationship.

For example:

```text
index record
```

with no:

```text
SOURCE_TO_GRAPH
GRAPH_TO_SOURCE
```

That's a provenance orphan.

I would call it:

```text
PROVENANCE_ORPHAN
```

This is potentially more serious than dead code.

---

# 31. Broken relationships

If:

```text
A CALLS B
```

but B no longer exists in the same revision:

```text
DANGLING_EDGE
```

Likewise:

```text
config references missing handler
test targets missing object
registration points to nonexistent callable
```

Those should be easy to surface.

---

# 32. Ambiguity density

Because you've got:

- 42,836 uniquely resolved calls
- 72,614 ambiguous
- 159,153 unresolved

we can use those counts structurally.

Not as quality scores.

For each parent:

```text
resolved_calls
ambiguous_calls
unresolved_calls
external_calls
dynamic_calls
```

Then parents with unusually high unresolved mass become:

```text
LOW_VISIBILITY_REGION
```

Not “bad code.”

Simply:

> static graph can't see this area clearly.

That's important for security because attackers love blind spots.

---

# 33. Dynamic-boundary candidates

High unresolved density + privileged capability = priority.

Example:

```text
plugin loader
dynamic call mass = high
filesystem/network capability = high
```

That deserves runtime instrumentation.

Thus static graph tells TrueCog **where runtime witnesses are needed**.

---

# 34. Runtime versus static graph

Ultimately we want two separate evidence channels.

```text
STATIC GRAPH
what code permits / declares
```

and:

```text
RUNTIME GRAPH
what actually happened
```

Never merge them silently.

Then compare.

Example:

```text
static: A may call B
runtime: never observed
```

or:

```text
runtime: A reached B
static: unresolved/dynamic
```

Both are useful.

---

# 35. Historical/revision graph

Later:

```text
revision A
→ revision B
→ revision C
```

Objects can retain lineage:

```text
introduced
modified
moved
renamed
deleted
replaced
superseded
```

Then security can ask:

> When did this privileged path appear?

Or:

> Which commit introduced this bypass?

---

# 36. Relationship overtaking in code

Same law we discovered with text.

A nearby relationship may become more locally prominent as traversal moves.

But the underlying code relationship doesn't cease to exist.

So:

```text
local traversal lead changes
≠
ownership changes
```

For code, ownership changes only through explicit structure.

Codex already got this right. 

---

# 37. Suggested graph views

Rather than one monster graph, I'd expose named views.

### Structural

```text
STRUCTURE_VIEW
```

Ownership hierarchy.

### Dependency

```text
DEPENDENCY_VIEW
```

Calls/imports/references.

### Position

```text
SOURCE_ORDER_VIEW
```

Local structural neighborhood.

### Orphan

```text
ORPHAN_VIEW
```

Disconnected or weakly connected objects.

### Security

```text
AUTHORITY_BOUNDARY_VIEW
```

Low → high authority paths.

### Mutation

```text
MUTATION_VIEW
```

Who can change state?

### Test

```text
TEST_WITNESS_VIEW
```

Which relationships are tested?

### Provenance

```text
PROVENANCE_VIEW
```

Source → derivative → consumer.

### Runtime

```text
RUNTIME_VIEW
```

Later CompuCog observations.

---

# 38. Query result format

Every query should return something like:

```text
query receipt
repository revision
graph revision
method
center object

locations[]
relationships[]

channels:
  ownership
  dependency
  position
  tests
  provenance
  runtime

unresolved[]
truncated?
```

And:

```json
"answer": null
```

That's fucking important.

The operator follows the evidence.

---

# 39. No automatic deletion

Graph analysis must NEVER become:

```text
orphan detected
→ delete file
```

Absolutely not.

Instead:

```text
ORPHAN_CANDIDATE
→ exact locations
→ supporting relationship evidence
→ human/operator review
```

Then action happens separately.

Same architecture again:

**locate → evidence → adjudicate → act.**

---

# 40. First useful security query set

Once the existing map is stabilized, I'd run these before even adding CFG:

1. **Show every callable external entrypoint.**
2. **Show every filesystem-writing function.**
3. **Show every process-execution surface.**
4. **Show every direct TrueMem caller.**
5. **Show every TrueCore bypass candidate.**
6. **Show every agent/tool registration surface.**
7. **Show all security-related config writers.**
8. **Show all canonical evidence writers.**
9. **Show every privileged sink with zero tests.**
10. **Show every privileged sink reachable through unresolved calls.**
11. **Show disconnected packages/subgraphs.**
12. **Show functions/classes with no incoming graph edges.**
13. **Show docs that claim capabilities absent from code.**
14. **Show code capabilities absent from documentation.**
15. **Show duplicate/parallel implementations of security-sensitive functionality.**

That alone could be extremely revealing.

---

# 41. The next generation after that

Once control/data flow is trustworthy:

```text
untrusted input
→ actual data path
→ actual branch path
→ privileged mutation
```

Then TrueCog gets its real boundary scanner.

That's where you can ask:

> **Where can shit actually slip through?**

Not theoretically.

From exact source evidence.

---

# 42. The guiding law

I would put this at the top of the graph specification:

> **The graph does not score truth, safety, correctness, ownership, or vulnerability. It preserves and measures relationships so an operator can locate and verify those properties from exact source evidence.**

And directly under it:

> **Weights are measured traversal channels, never authority.**

That's consistent with everything we've built today.

---

## Condensed architecture

```text
                           REPOSITORY
                               │
                   ┌───────────┼───────────┐
                   │           │           │
               OWNERSHIP    POSITION    DEPENDENCY
                   │           │           │
                   └───────────┼───────────┘
                               │
                         CODE OBJECTS
                               │
        ┌──────────────┬───────┼────────┬───────────────┐
        │              │       │        │               │
     SECURITY        ORPHAN   TEST   PROVENANCE     MUTATION
        │              │       │        │               │
        └──────────────┴───────┼────────┴───────────────┘
                               │
                         EXACT LOCATIONS
                               │
                         ORIGINAL SOURCE
```

Later:

```text
                  STATIC CODE GRAPH
                         +
                 COMPUCOG RUNTIME GRAPH
                         +
                  TRUEVISION/HID STATE
                         +
                   AUTHORITY GRAPH
                         │
                         ▼
                    TRUECOG AUDIT
```

That's what I would tell Codex we want.

**Not a prettier code graph.**

A **source-grounded investigative graph of structure, authority, provenance, mutation, testing, dead/orphan state, and eventually actual execution/data flow—where every relationship can be walked back to exact evidence.**
