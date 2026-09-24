# Parameterized evidence-study operator method

This is the mandatory detailed method for parameterized evidence studies. Read the repository-root `AGENTS.md` first. This file relocates the study-specific instructions from that front door without changing their requirements.

## 6. Required study lifecycle

Every parameterized evidence study follows these gates in order. A phase may be
short when the data is already clean, but it may not be silently skipped.

### Gate 0 — establish scope and custody

Before reading or downloading data:

- identify the repository/component boundary;
- identify whether the request authorizes read-only inspection, acquisition,
  local writes, system changes, external publication, or destructive action;
- locate existing work, provenance, reports, and prior task artifacts;
- preserve unrelated user changes in dirty worktrees;
- resolve the exact source path or URL;
- decide where raw data, derived data, user deliverables, and test outputs belong;
- do not place large datasets or generated results in a source repository unless
  explicitly requested;
- never expose a password, token, private key, cookie, or secret-bearing file.

### Gate 1 — request or acquire data

If data is absent, ask the human for the smallest useful source or request
authority to retrieve it. Say what formats are usable, but do not make the human
pre-clean the source for the agent's convenience.

When data is supplied:

- treat it as immutable source evidence;
- compute a cryptographic hash when practical;
- record byte size, retrieval time, source identity, revision/version, license,
  and access method;
- retain compressed originals when they are the provenance object;
- distinguish recovered, reconstructed, adapted, modeled, and directly observed
  data in filenames and records;
- never rename a derived reconstruction as raw data.

When acquiring current web data:

- pin a revision, timestamp, query, or content hash when possible;
- retain enough response metadata to reproduce the request;
- distinguish a current snapshot from historical data;
- do not join across epochs merely because identifiers match;
- record failed downloads, throttling, partial files, and retries.

### Gate 2 — inventory and profile before interpretation

The operator must inspect the actual source and report at least:

- file/container formats and compression;
- exact column or field names;
- physical/logical types;
- row, object, event, file, and partition counts as applicable;
- distinct identity counts;
- null and non-null counts;
- categorical value counts using exact source strings;
- minimum/maximum timestamps and explicit timezone assumptions;
- timestamp resolution and sampling cadence;
- duplicate keys and repeated observations;
- units and plausible ranges;
- candidate identifiers and join keys;
- constant, near-constant, sparse, or missing fields;
- fields that are flags rather than measurements;
- fields derived upstream rather than directly observed;
- source-specific status vocabularies;
- potential state-machine sibling fields;
- schema drift across files/partitions;
- whether the source contains the identity needed by the human's likely question.

Do not infer semantics from a column name alone. Inspect values, distributions,
source documentation, and generating code where available. `snr_bad` is not SNR
in decibels. A `switch` flag is not a handover duration. A TLE is not network
telemetry. A model reanalysis value is not an on-site instrument reading.

### Gate 3 — shape data reversibly

Shaping means producing documented analysis surfaces while keeping raw source
bytes unchanged. The operator may:

- decode containers;
- normalize machine-readable types;
- derive UTC timestamps while retaining original timestamps;
- construct explicit windows;
- select one observation per declared identity/time key;
- add null-preserving derived columns;
- construct joins whose keys and tolerances are recorded;
- split one source into semantically distinct layers;
- produce compact Parquet/CSV/JSON analysis tables;
- build indexes and caches outside the source repository.

Every derived field must have:

- a stable name;
- a definition;
- source fields;
- units;
- null behavior;
- aggregation rule;
- temporal alignment rule;
- authority class: authoritative, derived, proxy, counterfactual, or
  presentation-only.

Never overwrite raw fields with derived values. Never fill an unavailable
measurement with zero. Never collapse null, false, not-applicable, censored, and
not-observed into one state. Never silently discard rows that would change the
study population.

### Gate 4 — separate evidence layers

Create one named layer for each distinct source epoch, observation authority,
resolution, and semantic level. Typical separations include:

- device/user telemetry versus infrastructure telemetry;
- event/status history versus current geometry;
- observed measurements versus modeled weather;
- historical data versus current catalog snapshot;
- per-object records versus aggregate windows;
- operator labels versus source labels;
- training data versus reserved evaluation data;
- factual evidence versus presentation-only charts.

Each layer records:

- `layer_id`;
- source reference and SHA-256;
- observed fields;
- UTC time range and resolution;
- authority statement;
- allowed question IDs;
- prohibited joins;
- known missing identities/fields;
- derived table location and receipt.

If two layers cannot honestly answer the same event-level question, add an
explicit `FORBID_JOIN` rule. Do not rely on prose memory to keep them separate.

### Gate 5 — explain capability, then ask what the human wants to know

After profiling and shaping, the operator gives the human a short data contract:

- what is actually present;
- what time period is covered;
- what entities are represented;
- what measurements, flags, statuses, and derived fields exist;
- what identities or physical quantities are absent;
- what questions are directly answerable;
- what questions are answerable only through a named proxy or counterfactual;
- what questions are not answerable from these layers.

Then ask: **What do you want to know from this data?**

In equivalent wording, ask the human what they wish to know from the shaped
data.

Offer a small set of well-formed example questions when helpful. Keep examples
within the observed fields. Do not lead the human toward a dramatic conclusion.
Do not ask the human for window size, statistical test, eccentricity cutoff, or
other implementation parameters at this stage.

### Gate 6 — compile questions into evidence obligations

For every requested question, create a stable `question_id` and record:

- original wording;
- target population/entity;
- relevant layers;
- required fields;
- unavailable fields;
- date/time bounds;
- quantity and units;
- comparison groups;
- polarity/direction;
- answer class: `MEASUREMENT`, `DESCRIPTIVE`, `PROXY`, or `COUNTERFACTUAL`;
- evidence needed to support the answer;
- evidence that would refute it;
- termination condition;
- expected limitations.

Split compound questions. “Did a satellite fail and neighboring satellites take
its users?” contains at least a status-transition obligation, serving-satellite
identity obligation, neighbor-definition obligation, user/load obligation, and
time-alignment obligation. Missing one means the full causal claim is unsupported.

### Gate 7 — agent chooses technical parameters

The operator agent chooses technical parameters after inspecting the data and
before seeing results under competing parameter values. The agent must not tune a
threshold until a desired answer appears.

Parameters include, when relevant:

- operational/status vocabulary;
- inclusion and exclusion criteria;
- altitude, eccentricity, speed, quality, or other thresholds;
- time-window width and alignment;
- event start/end rules;
- persistence/debounce rules;
- missingness policy;
- deduplication key and tie breaker;
- join key, direction, and tolerance;
- interpolation policy;
- baseline window and minimum baseline observations;
- recovery tolerance, sustained-duration rule, and censoring horizon;
- neighbor definition;
- proxy formula;
- counterfactual assumptions;
- statistical test and alternative;
- multiple-comparison policy;
- minimum coverage/sample requirements;
- outlier handling;
- confidence interval/bootstrap settings;
- random seed;
- hardware/backend and fallback policy;
- output precision;
- chart scales, bin widths, ordering, and labels;
- resource ceilings and maximum service calls.

For each parameter record:

- stable `parameter_id`;
- typed value;
- `set_by: agent` by default;
- rationale;
- evidence basis from the profiled source or an authoritative method contract;
- affected question IDs;
- lock state.

If the human changes a proposed value, record `set_by: human_override`, preserve
the agent-proposed value, and record the override reason. Never rewrite an
override so it appears agent-derived.

The agent should ask the human to choose only when:

- two defensible choices encode materially different meanings;
- the correct meaning cannot be inferred from the request or data;
- the choice changes external cost, risk, publication, or destructive scope;
- domain policy belongs to the human rather than the analysis method.

### Gate 8 — freeze before computation

No result-producing computation may begin until:

- data layers and hashes are recorded;
- questions and answer classes are fixed;
- required/unavailable fields are recorded;
- all technical parameters are locked;
- isolation rules are explicit;
- expected outputs and receipts are declared;
- chart label rules are declared;
- claim audit is required.

Use:

```bash
cd TrueCore
PYTHONPATH=. python -m truecore.agents.parameterized_study validate PLAN.json
PYTHONPATH=. python -m truecore.agents.parameterized_study freeze PLAN.json --output FREEZE.json
```

The freeze receipt's `frozen_plan_sha256` is the computation gate. If a parameter
changes afterward, create a new plan version and hash, explain the change, and
rerun every affected result. Do not edit a frozen plan in place.

### Gate 9 — compute through real tools

- Run only code that exists and whose entrypoint has been inspected.
- Prefer deterministic, headless commands with explicit input/output paths.
- Do not create a project `.venv` unless the repository contract explicitly
  requires one. Prefer the existing runtime or ephemeral dependency execution.
- Keep raw data read-only.
- Write generated data and logs outside source repositories unless outputs are
  explicitly repository-native.
- Capture stdout, stderr, exit status, versions, and timing.
- Use UTC timestamped filenames for run artifacts.
- Preserve failed-attempt logs and durations when they teach anything about the
  real execution path.
- Do not claim a stage completed when it exited nonzero or stopped before output
  validation.
- Do not silently fall back from XPU/GPU to CPU when the backend is part of the
  claim.
- Do not replace missing values, identities, or measurements with estimates
  unless the frozen plan explicitly defines and labels an estimation model.

### Gate 10 — inspect raw relationships before aggregate interpretation

Before describing a feature as explanatory:

- determine whether it is a physical measurement, thresholded measurement,
  flag, status, alert, label, or derived aggregate;
- cross-tab flags/statuses against outcome codes at the finest available raw
  resolution;
- inspect whether predictor and outcome are emitted by the same device state
  machine;
- check temporal ordering; a co-reported flag cannot establish that it preceded
  or caused an event;
- inspect sparsity, constant values, and field coverage;
- separate co-reported state from explanatory covariates;
- remove tautological or sibling fields from explanatory rankings while retaining
  them in a clearly labeled state-agreement analysis;
- state when a relationship may merely mean “the system agrees with itself.”

Never compare binary flag rates to physical measurements as though they share
units. Never describe a Boolean SNR flag as signal strength, fade depth, RF
margin, or decibels.

### Gate 11 — classify claims before writing them

Every material result belongs to exactly one claim class:

- **Observed measurement:** directly present in source records with units.
- **Source status/label:** directly emitted by the source but potentially
  generated by its own classifier or state machine.
- **Derived measurement:** mechanically computed from observed fields under a
  frozen rule.
- **Association:** a statistical relationship without causal authority.
- **Proxy:** a named substitute for an unavailable target, with its formula and
  limitations retained everywhere.
- **Counterfactual:** output of an explicit what-if model, not observed behavior.
- **Inference:** operator reasoning supported by evidence but not directly stored.
- **Limitation:** a statement about unavailable evidence or unsupported claims.

Do not promote one class to another. In particular:

- association is not causation;
- status transition is not service withdrawal unless the source defines it so;
- catalog disappearance is not proven hardware failure;
- geometry availability is not control-plane reassignment;
- equal-share pressure is not measured load;
- RAAN proximity is not slot adjacency;
- modeled weather is not terminal-local weather measurement;
- a five-minute window cannot prove sub-second handover dynamics;
- a serving-satellite inference is not serving identity;
- a patent describes capabilities, not necessarily deployed policy;
- a flag/outage overlap may be state-machine co-reporting, not physics.

### Gate 12 — charts and dashboards

Charts are part of the claim surface and obey the same evidence laws.

- Use the exact metric name, including `flag`, `rate`, `proxy`, `modeled`,
  `counterfactual`, `inferred`, or `geometry-only` where applicable.
- A proxy name must remain in the output filename, data columns, chart title,
  axis labels, tooltip, legend, and explanatory text.
- Never label `bad_snr_flag_fraction` as “SNR” or “signal strength.”
- Put units on axes.
- Put sample size and coverage near sparse metrics.
- Mark right-censored observations and search horizons.
- Keep zero distinct from missing.
- Do not truncate axes in ways that manufacture dramatic differences.
- Use consistent scales for comparisons.
- State when dates/rows come from separate source layers.
- Do not place current geometry in a historical performance timeline.
- Distinguish the source's status vocabulary from an analyst classification.
- Separate co-reported-state panels from explanatory-feature panels.
- Display failed or unavailable metrics as such; do not omit them silently.
- Validate charts at narrow and wide sizes and in light/dark themes when they are
  part of an interactive surface.

### Gate 13 — operational verification and reproducibility

For every new system, installation, integration, repository change, or
meaningful configuration change:

- resolve the governing instruction chain and authorized production route;
- exercise that route against real runtime state and observe the requested effect;
- retain UTC timestamped operation receipts outside the source repository under
  `/home/lamercey/Documents/User System Test` without overwriting prior evidence;
- inspect the route's refusal and failure behavior where the actual operation
  exposes those branches;
- run syntax/static checks without producing avoidable bytecode caches;
- run `git diff --check`;
- inspect `git status --short` and distinguish pre-existing changes from new work;
- report exact operation and receipt paths, or the authority gap that prevented
  operational verification.

Diagnostic scripts do not prove another operation. Do not create a standing
synthetic acceptance or verification suite.

Acceptance for a parameterized study must prove at least:

- plans missing data, questions, parameters, or output rules are rejected;
- unlocked parameters cannot open the computation gate;
- direct human-set parameters are rejected unless recorded as human overrides;
- overrides preserve the agent proposal and reason;
- duplicate IDs are rejected;
- unknown layers/questions are rejected;
- forbidden cross-layer joins are rejected;
- valid plans freeze deterministically;
- semantically identical mappings produce identical hashes;
- no evidence, relationship, or answer authority is created by the freeze tool.

## 7. Parameter derivation doctrine

When selecting a threshold from data:

1. identify the reference population before examining target outcomes;
2. use a distributional property of the reference population or an authoritative
   external standard;
3. record the exact statistic and rounding;
4. ensure target/outcome rows did not leak into threshold fitting unless the
   method explicitly requires them;
5. preserve a sensitivity analysis when nearby defensible values matter;
6. name the threshold as an analyst rule, not a source field;
7. never retune after viewing favorable results without versioning it as a new
   exploratory analysis.

When defining events:

- use a stable identity;
- define start, end, persistence, gap, and censoring rules;
- specify daily versus hourly versus sample-level resolution;
- do not interpolate beyond source resolution;
- handle status chatter explicitly;
- ignore pre-operational launch/raising chatter when the question concerns final
  withdrawal;
- require the target transition after the final qualifying baseline state when
  using a “last operational -> first dying” rule.

When defining neighbors:

- state the geometry and coordinate system;
- use circular differences for circular coordinates;
- distinguish same shell, same plane, adjacent plane, orbital slot, nearest in
  three-dimensional position, and nearest visible from a terminal;
- never imply user transfer without assignment/load data;
- retain the proxy identifier in every output field.

When defining recovery:

- define baseline population and minimum observations;
- define acceptable bands per metric;
- require sustained recovery when one good sample would be unstable;
- set a search horizon before computation;
- classify unrecovered-within-horizon as right-censored;
- do not claim the event never recovered.

## 8. Question and layer isolation law

One question may use multiple layers only when all of the following hold:

- the layers cover compatible epochs or the question explicitly compares epochs;
- entity identities are valid across sources;
- join keys are observed or the inference model is frozen and labeled;
- time resolutions support the requested event timing;
- source authorities do not conflict;
- no `FORBID_JOIN` rule applies;
- the final claim remains within the weakest layer's evidence boundary.

If not, split the question. Run separate analyses and compare only at the level
they share. A 2023 status archive, November 2024 terminal trace, and September
2026 TLE snapshot are three layers, not one event stream.

## 9. Missing-data and null law

- `null` means unavailable/unknown according to the field contract, not zero.
- `false` means the source explicitly reports false.
- `not_applicable` means the field does not apply.
- `not_observed` means the collection opportunity did not occur.
- `censored` means the value may exist outside the observation horizon.
- `not_exposed` means the system may know it but the dataset/API does not reveal
  it.
- `derived_unavailable` means required inputs for a derived field were missing.

Keep these states separate whenever the source permits. Report coverage for each
ranked field. A constant field cannot discriminate and must not be ranked as
though its absence of variation were evidence of no physical effect.

## 10. Statistical discipline

- Begin with descriptive counts and distributions.
- Define the unit of analysis and avoid treating correlated repeated samples as
  independent entities.
- Do not use p-values as effect sizes.
- Report effect direction, magnitude, coverage, and sample size.
- Treat univariate discrimination as screening, not explanation.
- Account for route, time, subject, device, shell, or other clustering when the
  question requires generalization.
- State when a test is exploratory.
- Freeze covariates before multivariate modeling.
- Diagnose leakage and sibling state fields.
- Keep held-out evaluation sealed when applicable.
- Do not claim population-wide behavior from one route, terminal, user, or event.
- Do not claim planned versus unexpected failure without independent labels.
- Preserve negative and null findings.

## 11. Timing and performance law

Time every material stage separately:

- source discovery/acquisition;
- extraction/decompression;
- profiling;
- shaping/adaptation;
- external API retrieval;
- joining;
- analysis;
- chart generation;
- acceptance validation.

Record wall time for user-visible latency. Record internal stage time when code
provides it. Record user/system CPU time when relevant. Identify dependency
resolution or first-run compilation separately from warm runs. Do not mix failed
attempt time into a successful-run time without labeling both. A fast wrong run
is not a performance success.
