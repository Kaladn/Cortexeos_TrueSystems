# TrueCog / CompuCog Security Architecture --- Working Design Record

**Status:** Design capture / investigation target\
**Date:** 2026-09-13\
**Purpose:** Preserve the security architecture discussed before
implementation. This is not a claim that every mechanism is already
implemented or security-qualified.

## 1. Core premise

TrueSystems security is based on **authority, provenance, witnessed
state, identity, and bounded capability**, rather than trusting an actor
merely because it can physically perform an operation.

> **Capability to perform an action is not authority to have that action
> accepted.**

A process may be able to write a file. An AI agent may be able to issue
a command. A peripheral may emit HID events. A network connection may
deliver bytes. None alone grants authority.

Every consequential transition should be attributable to an admitted
identity, an allowed capability, a current state, and a witnessed
provenance chain.

## 2. "True" means deterministic state truth

"True" does not mean the system claims universal truth. It means it can
truthfully report the deterministic state of admitted data: what was
admitted, exact source identity, where observations came from, what
relationships were measured, which actor performed an operation, what
existed before, what changed, and whether provenance remains valid.

The system may report **what the admitted data says**. It must not
silently promote that into worldwide truth.

If required evidence cannot be located, it must not manufacture the
missing bridge. Insufficient evidence is a valid result.

## 3. Immutable evidence law

Once source evidence is admitted, its content is immutable.

The system may create indexes, addresses, relationship graphs, temporary
projections, annotations, corrections, contradiction records,
supersession records, operator interpretations, and derived reports. It
may **not rewrite the admitted source**.

If admitted evidence changes, the provenance chain is broken. A
downstream conclusion might accidentally remain factually correct, but
it no longer has valid provenance to the admitted evidence.

### Witnessed incident

During current development, a hash-frozen canonical README was modified
by an authorized engineering agent while attempting a legitimate
documentation update. The filesystem allowed the write, but contract
validation detected that the protected artifact no longer matched its
admitted hash. The altered state was rejected from downstream
acceptance, canonical bytes were restored, and the failed attempt
remained visible in audit history.

> **A trusted actor performing a sensible operation is still rejected
> when the resulting state violates provenance law.**

Intent does not override evidence integrity.

## 4. Provenance-bound authority

Authority should attach to an admitted state, not merely a pathname,
filename, process name, username, AI model name, network address, or
object label.

Conceptually:

``` text
admitted object
+ content hash
+ provenance identity
+ role
+ integrity state
= admissible source state
```

If bytes change without an authorized admission event, the changed
object does not inherit the previous object's authority.

## 5. Mutable system files use a different law

Working repositories, logs, caches, configuration, generated artifacts,
and normal system state legitimately change.

The security question becomes:

> **Was this exact state transition performed by an admitted actor,
> through an admitted capability, against the expected prior state,
> under a current authorization state?**

A mutable transition may eventually carry a receipt containing:

``` text
object_id
previous_hash
writer_id
writer_class
capability_id
request_id
authorization_epoch
operation
new_hash
timestamp / monotonic sequence
result
```

The precise schema remains to be designed and tested.

## 6. Every actor is an identity

Treat every participant as an identifiable actor: human user, Codex,
local model such as Muse, bounded worker, system service, registered
peripheral, registered machine, registered mobile device, registered
camera, and relevant registered network connection/node.

Identity alone does not grant permission. Each identity receives only
authorized capabilities.

## 7. Human authentication is more than account authentication

The target question is not merely "does this request carry the user's
credentials?"

It is:

> **Is the registered human actually present, on an admitted device,
> during the current interaction, and is there evidence that the request
> arose from genuine local activity?**

Potential witness channels include registered workstation/mobile
sessions, camera-based presence and biometric matching, liveness/motion
evidence, registered keyboard/mouse activity, phone touch activity,
recent local unlock/biometric events, and timing continuity.

No one signal must become universal proof. Independent witnesses can be
combined according to action risk.

## 8. Privacy boundary: activity attestation, not keylogging

Keyboard and mouse observation should prove **activity**, not capture
content.

Useful derived state may include:

``` text
registered_keyboard_active = true
registered_mouse_active = true
last_keyboard_activity_age_ms = ...
last_mouse_activity_age_ms = ...
device_identity = ...
session_identity = ...
```

The system should not persist actual keys typed merely to prove physical
input.

Likewise, security video should favor derived presence/liveness/state
witnesses and bounded retention over indefinite raw surveillance
archives unless raw evidence is explicitly required.

## 9. Peripheral identity and "marriage"

Linux can distinguish activity from different HID/input devices, but
ordinary VID/PID, names, paths, and many serial identifiers are not
sufficient cryptographic identities.

### Future hardware concept --- PARKED

A future keyboard, mouse, or other peripheral should contain a **unique
protected cryptographic identity**.

Enrollment creates a marriage:

``` text
machine identity
↔ peripheral identity
↔ enrollment relationship
```

A married peripheral proves possession of its device secret through
challenge-response. An unknown or cloned device does not inherit
trusted-HID status merely because the OS recognizes it as a keyboard or
mouse.

Potential hardware approaches---including secure elements, protected
MCUs, TPM-like components, or purpose-built peripheral attestation
hardware---are **parked for later investigation**. No chip or
implementation is selected here.

## 10. TrueVision as an independent physical-world witness

TrueVision is not merely "camera recognizes face."

For security it can become an independent witness of physical state:
registered camera identity, expected observation path, human presence,
biometric match where authorized, liveness/motion, continuity over time,
state changes, and correlation with workstation/mobile activity.

A supplied photograph saying "the user is present" must not
automatically equal a live witnessed observation.

The longer-term target is to authenticate not only visual content but
the **observation path and temporal continuity** that produced it.

Raw video is massive; retention should be bounded and allowed to roll
off according to policy, while useful derived state/provenance records
may persist longer.

## 11. CompuCog / TrueCog is the security animal

SecureCore and CompuCog have different jobs.

**SecureCore:** bounded agent execution authority---what an agent may
call, which operations are admitted, and how actions remain constrained.

**CompuCog / TrueCog:** temporal/security observer---system activity
logging, state observation, lineage, change detection, anomaly
observation, actor attribution, provenance continuity, historical
comparison, and deployment of small bounded watchers/workers.

CompuCog's power comes from retaining a structured picture of **what the
machine was**, comparing it with **what the machine is**, and
identifying **what changed between those states**.

Do not depend primarily on human habit profiling. Human schedules and
behavior legitimately vary. "The user normally does X" is weaker than
witnessed current state.

The stronger question is:

> **What is different now, who caused it, through which admitted path,
> and was that transition authorized?**

## 12. Watchers and anomaly workers

Potential bounded workers include canonical evidence integrity,
mutable-file transitions, process identity, agent actions, HID
presence/activity, camera/presence, network nodes/connections, model
identity, tool/capability use, and configuration drift.

Workers report measured state and provenance rather than inventing
security conclusions beyond their contracts. Higher layers correlate
receipts.

## 13. Agent authority and external instructions

Codex, Muse, or another agent may read webpages, email, documents,
source files, model-generated text, and external tool output. Those
sources may contain instructions.

Their presence in model context does **not** make them authorized human
intent.

``` text
external content may influence reasoning
≠
external content possesses human execution authority
```

For consequential actions, the system may require a current chain of
human identity, device identity, presence witness, genuine
input/activity witness, agent identity, requested capability, target
state, and authorization state.

A malicious document cannot manufacture that chain merely by claiming
the user approved an action.

## 14. Risk-sensitive escalation

Not every action needs the same authentication burden.

-   **Low-risk read:** current authenticated session may suffice.
-   **Mutable working-file write:** admitted writer, capability,
    expected prior state, recent authenticated activity.
-   **Security configuration:** stronger human-presence/liveness and
    explicit authorization.
-   **Canonical evidence mutation:** never an in-place operation;
    corrections/new evidence are separately admitted.

## 15. Rotating canonical integrity concept

A rotating integrity epoch may be derived over canonical
datasets/protected state:

``` text
canonical files
→ deterministic object hashes
→ canonical manifest/root
→ authenticated daily/epoch derivation
→ short rotating system slot
```

The short value (for example five digits) is a **tripwire/fast
discriminator, never proof**.

Wrong slot: reject/flag immediately.\
Correct slot: continue full verification.

Full integrity still depends on complete cryptographic hashes and an
authenticated derivation. The construction requires later cryptographic
review and adversarial testing.

## 16. Provenance and rotating epochs together

Derived artifacts may eventually bind to:

``` text
source_root
source_revision
projection_generation
method_version
integrity_epoch
derived_artifact_hash
execution_receipt
```

Before reuse, verify that the artifact still corresponds to admitted
source state. This can expose stale projections, rollback/replay, source
mutation, wrong-dataset artifacts, cross-generation IDs, and
unauthorized substitution.

## 17. Zero-click relevance --- bounded claim

Do **not** currently claim this stops zero-click attacks. A zero-click
exploit may still execute through a vulnerable parser, service, decoder,
network component, or application.

The potential value is:

> **Compromise should not automatically confer authority.**

Even if malicious code executes, it should have difficulty acquiring the
current combination of registered actor identity, human presence,
admitted device witnesses, valid capability, expected target state,
current integrity epoch, and provenance continuity.

This may reduce blast radius and expose unauthorized post-exploitation
actions. It requires dedicated adversarial testing.

## 18. Security state as a graphable machine history

With registered identities and receipts, the machine can be viewed as a
provenance graph:

``` text
actor
→ device
→ session
→ request
→ capability
→ target object
→ prior state
→ operation
→ resulting state
→ downstream dependencies
```

This permits questions such as: Who changed this file? Was the writer
registered? Was the human present? Which device supplied the witness?
Which agent received the request? Which capability authorized it? What
was the previous hash? What downstream artifacts depend on it? Did it
coincide with an unknown process/node? Is the transition reproducible?

The graph is a view over evidence; it is not permission to rewrite
evidence.

## 19. Existing precedents

### TrueVision

Existing state-recognition work already separates observation from
generation, produces hashable reports, preserves source-truth
boundaries, and declares bounded callable capabilities. Those ideas may
contribute to security witnessing, but state recognition is not
automatically an authentication system.

### Cognitive Authenticator

Earlier work explored typing dynamics, language patterns, interaction
patterns, drift, session authentication, and rotating daily passphrases.

The **conceptual direction**---multi-signal identity
continuity---remains useful. The old implementation is not modern
security authority. Prototype similarity scoring, predictable passphrase
derivation, and emergency fallback behavior must not be promoted merely
because they exist.

Historical code is evidence of prior thinking, not a frozen current
contract.

## 20. Registration / deployment ceremony

A serious deployment may begin with explicit registration of authorized
humans, AI agents, machines, phones/tablets, cameras, peripherals,
services, relevant network nodes/connections, callable workers/tools,
canonical datasets, mutable system areas, and capability contracts.

Expansion to multiple users/machines must preserve identities rather
than collapsing everything into "trusted network" or "logged-in user."

## 21. Failure should preserve evidence

A rejected operation is useful evidence. Avoid cleanup that makes the
attempted transition disappear.

Where practical retain attempted actor, target, requested operation,
prior state, attempted state, rejection reason, restoration/recovery
action, final state, and receipt hashes.

The frozen-file incident is valuable precisely because the failed
transition remained inspectable.

## 22. Principles to freeze for later investigation

1.  Capability is not authority.
2.  Admitted evidence is immutable.
3.  Derived views may change; source evidence does not.
4.  Mutable changes require attributable authorized transitions.
5.  Every human, AI, device, worker, and relevant node has identity.
6.  Identity does not automatically grant capability.
7.  External content does not inherit human intent.
8.  Consequential actions should have independently witnessed
    presence/intent.
9.  Activity attestation should avoid unnecessary content surveillance.
10. Unknown peripherals do not automatically become trusted witnesses.
11. TrueVision can become a physical-world witness.
12. CompuCog/TrueCog owns temporal security observation, lineage, and
    anomaly witnessing.
13. SecureCore owns bounded agent execution; it is not the whole
    security system.
14. Short rotating hash slots are tripwires, never cryptographic proof.
15. Security decisions bind to expected prior state and current
    provenance.
16. Rejected transitions remain auditable.
17. No zero-click-prevention claim until adversarially demonstrated.
18. Compromise should not automatically acquire authority.

## 23. Parked future investigations

Do not implement these merely because they are recorded here:

-   cryptographically married keyboards/mice;
-   secure-element or TPM-like peripheral hardware;
-   challenge-response peripheral enrollment;
-   machine-to-phone marriage;
-   camera/device attestation;
-   biometric/liveness fusion;
-   rotating canonical-integrity epochs;
-   short rotating integrity slots;
-   writer/state-transition receipts;
-   network-node registration;
-   multi-witness authorization;
-   adversarial zero-click/post-exploitation testing;
-   replay/rollback resistance;
-   symlink/substitution/path-confusion tests;
-   malicious peripheral emulation;
-   provenance-graph security queries.

Each needs a threat model, acceptance criteria, privacy review, and
adversarial tests before promotion.

## 24. Immediate architectural target

The immediate objective is **not** to build every security idea above.

First complete and lock the current TrueSystems/Delving work into its
proven boundaries. Then TrueCog/CompuCog investigation can begin
from a clean premise:

> **Observe state. Preserve provenance. Identify actors. Bound
> capabilities. Authenticate consequential transitions. Fail closed when
> the chain is broken.**

The accidental frozen-file incident should be retained as an early
fixture because it demonstrated a foundational property already present:

> **The ability to change state did not grant authority to have the
> changed state accepted.**
