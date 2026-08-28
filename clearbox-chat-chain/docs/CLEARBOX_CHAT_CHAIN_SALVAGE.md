# Clearbox Chat-Chain Salvage

## Purpose

Provide one chat surface that can:

1. send a conversation turn through one model;
2. send a conversation turn through an ordered chain of models;
3. preserve the resulting conversation state;
4. continue from any completed assistant or model output; and
5. optionally branch from an earlier message.

Nothing else belongs in this system.

## External attachment custody

Chat/Chain may own the placement and continuity record for a validated
`clearbox.chain-attachment/1.0.0` document. The referenced subsystem continues
to own the artifact bytes, state, evidence, truth status, and interpretation.
Chat/Chain stores and projects the immutable reference only; it never resolves,
fetches, caches, copies, renders, summarizes, searches, scores, promotes, or
mutates the artifact.

Placement is declared only through the frozen contract's namespaced
`extensions.org.clearbox.chat-chain.placement` object. It identifies the branch
and one of `conversation`, `message`, or `model_output`; message and output
placements include their target ID. Branch projections inherit only references
that existed at the fork and were within its conversational cutoff. Continue
does not copy rows: visibility is derived from the original attachment record.

The runtime reads the canonical Draft 7 schema from
`$CLEARBOX_CONTRACT_ROOT/schemas/chain-attachment.schema.json`; local development
defaults to `/home/lamercey/ClearboxAI-V2.5/contracts/v1`. Validation uses the
host's existing `fastjsonschema` package and resolves shared schemas locally.
Chat/Chain contains no copied or forked Clearbox contract.

## Non-goals

The salvage system does not contain:

- lexicon management;
- 6-1-6 mapping;
- retrieval or LakeSpeak;
- citations or notes;
- tools or tool execution;
- plugins;
- nodes or distributed jobs;
- document ingestion;
- monitoring dashboards;
- model routing heuristics;
- model-written operational state;
- UI-owned conversation or chain state.

Those systems may exist elsewhere. They are not dependencies of Chat-Chain.

## Custody law

```text
The backend owns conversations, branches, messages, turns, chain runs,
model outputs, checkpoints, and active execution state.

The UI displays backend projections and submits user commands.

If the backend stops, the UI has no conversation state.
If the UI stops, an accepted backend operation continues or remains recoverable.
```

## System shape

```text
Browser
  |
  | commands and projections
  v
Chat-Chain Backend
  |-- Conversation Service
  |-- Turn Executor
  |-- Model Adapter Registry
  |-- Durable Repository
  `-- Event Stream
        |
        v
Model Runtimes
  |-- local model adapter
  `-- remote model adapters
```

There is one backend authority. Model runtimes generate text; they do not own
conversation state.

## Core records

### Conversation

```pseudo
record Conversation:
    id: UUID
    title: String
    root_branch_id: UUID
    created_at: Timestamp
    updated_at: Timestamp
    revision: Integer
```

### Branch

```pseudo
record Branch:
    id: UUID
    conversation_id: UUID
    parent_branch_id: UUID?
    forked_from_output_id: UUID?
    kind: main | continue | branch
    created_at: Timestamp
    revision: Integer
```

The main conversation is a branch. Continue and Branch create child branches.
There is no special side-chat storage system.

### Message

```pseudo
record Message:
    id: UUID
    conversation_id: UUID
    branch_id: UUID
    parent_message_id: UUID?
    role: user | assistant
    content: String
    created_at: Timestamp
```

An assistant message is the final surfaced answer for a turn. Individual model
outputs are stored separately so any one of them can be continued.

### Model seat

```pseudo
record ModelSeat:
    provider: String
    model: String
```

### Execution plan

```pseudo
record ExecutionPlan:
    mode: single | chain
    seats: List<ModelSeat>  // exactly one for single; one or more for chain

invariant:
    seats is not empty
    seats is ordered
    mode == single implies length(seats) == 1
```

### Turn

```pseudo
record Turn:
    id: UUID
    conversation_id: UUID
    branch_id: UUID
    user_message_id: UUID
    plan: ExecutionPlan
    status: accepted | running | completed | failed | cancelled
    current_step: Integer
    final_assistant_message_id: UUID?
    error: String?
    created_at: Timestamp
    updated_at: Timestamp
    revision: Integer
```

The plan is copied into the turn when accepted. Later UI configuration changes
cannot alter an in-progress or historical turn.

### Model output

```pseudo
record ModelOutput:
    id: UUID
    turn_id: UUID
    ordinal: Integer
    seat: ModelSeat
    content: String
    status: completed | failed
    error: String?
    created_at: Timestamp

invariant:
    ordinal is unique within turn
```

Every completed model output is addressable. This is what makes Continue from
any output possible.

## Context rule

```pseudo
function build_branch_context(branch_id):
    ancestry = load_branch_ancestry(branch_id)
    messages = load_messages_along_ancestry(ancestry)
    return messages ordered by conversational position
```

A child branch sees history through its fork point, followed by its own
messages. It does not see sibling-branch messages.

For a chain step:

```pseudo
function build_step_context(turn, ordinal):
    context = build_branch_context(turn.branch_id)
    prior_outputs = model_outputs.for_turn(turn.id).where(output.ordinal < ordinal)

    return:
        conversation = context
        current_user_message = message(turn.user_message_id)
        prior_chain_outputs = prior_outputs ordered by ordinal
```

Each later model receives the ordered prior outputs. It is instructed to build
on them and produce the next candidate answer.

## Commands

The UI may submit only these mutating commands.

### Create conversation

```pseudo
command CreateConversation:
    title: String?

function handle(command):
    conversation = create_conversation()
    main = create_branch(conversation, kind = main)
    conversation.root_branch_id = main.id
    commit(conversation, main)
    return conversation_projection(conversation.id)
```

### Send turn

```pseudo
command SendTurn:
    conversation_id: UUID
    branch_id: UUID
    content: String
    plan: ExecutionPlan
    expected_branch_revision: Integer
    idempotency_key: String

function handle(command):
    validate_content(command.content)
    validate_plan(command.plan)

    with transaction:
        branch = require_branch(command.branch_id)
        assert branch.conversation_id == command.conversation_id
        assert branch.revision == command.expected_branch_revision

        user_message = append_message(
            branch = branch,
            role = user,
            content = command.content,
            parent = branch.last_message_id
        )

        turn = create_turn(
            branch = branch,
            user_message = user_message,
            plan = immutable_copy(command.plan),
            status = accepted
        )

        advance_branch_revision(branch)
        commit()

    enqueue ExecuteTurn(turn.id)
    return {turn_id, user_message_id, branch_revision}
```

### Continue from output

Continue always starts a child branch at the selected completed output.

```pseudo
command ContinueFromOutput:
    output_id: UUID
    additional_instruction: String?
    plan: ExecutionPlan
    idempotency_key: String

function handle(command):
    source = require_completed_model_output(command.output_id)
    source_turn = require_turn(source.turn_id)

    with transaction:
        branch = create_branch(
            conversation_id = source_turn.conversation_id,
            parent_branch_id = source_turn.branch_id,
            forked_from_output_id = source.id,
            kind = continue
        )

        seed = append_message(
            branch = branch,
            role = assistant,
            content = source.content,
            parent = source_turn.user_message_id
        )

        instruction = additional_instruction
            or "Continue from this output without repeating completed material."

        user_message = append_message(
            branch = branch,
            role = user,
            content = instruction,
            parent = seed.id
        )

        turn = create_turn(branch, user_message, immutable_copy(command.plan))
        commit()

    enqueue ExecuteTurn(turn.id)
    return {branch_id, turn_id}
```

The backend loads the selected output. The browser never copies authoritative
output text into a Continue request.

### Branch from message

Branch is an explicit alternate direction from an earlier user or assistant
message.

```pseudo
command BranchFromMessage:
    message_id: UUID
    new_user_content: String
    plan: ExecutionPlan
    idempotency_key: String

function handle(command):
    source = require_message(command.message_id)

    with transaction:
        branch = create_branch(
            conversation_id = source.conversation_id,
            parent_branch_id = source.branch_id,
            forked_from_output_id = null,
            kind = branch
        )

        set_branch_fork_point(branch, source.id)
        user_message = append_message(branch, user, command.new_user_content, source.id)
        turn = create_turn(branch, user_message, immutable_copy(command.plan))
        commit()

    enqueue ExecuteTurn(turn.id)
    return {branch_id, turn_id}
```

### Cancel turn

```pseudo
command CancelTurn:
    turn_id: UUID
    expected_turn_revision: Integer

function handle(command):
    turn = require_turn(command.turn_id)
    assert turn.revision == command.expected_turn_revision
    assert turn.status in [accepted, running]
    mark_cancel_requested(turn)
    model_adapter.cancel_if_supported(turn.id)
    commit()
```

## Turn execution

Single-model and chained turns use the same executor.

```pseudo
function execute_turn(turn_id):
    turn = lease_turn(turn_id)
    transition(turn, running)

    try:
        for ordinal from turn.current_step to length(turn.plan.seats) - 1:
            assert_not_cancelled(turn)

            seat = turn.plan.seats[ordinal]
            context = build_step_context(turn, ordinal)
            result = model_registry.adapter_for(seat.provider).generate(
                model = seat.model,
                context = context
            )

            output = persist ModelOutput(
                turn_id = turn.id,
                ordinal = ordinal,
                seat = seat,
                content = result.content,
                status = completed
            )

            turn.current_step = ordinal + 1
            commit(turn, output)
            publish ModelOutputCompleted(turn.id, output.id)

        final_output = last_completed_output(turn.id)
        assistant_message = append_message(
            branch = turn.branch_id,
            role = assistant,
            content = final_output.content,
            parent = turn.user_message_id
        )

        turn.final_assistant_message_id = assistant_message.id
        transition(turn, completed)
        commit(turn, assistant_message)
        publish TurnCompleted(turn.id, assistant_message.id)

    catch cancellation:
        transition(turn, cancelled)
        commit(turn)
        publish TurnCancelled(turn.id)

    catch error:
        persist failed ModelOutput when a model call was attempted
        turn.error = safe_error(error)
        transition(turn, failed)
        commit(turn)
        publish TurnFailed(turn.id, turn.error)
```

Completed outputs survive a later step failure. The user may Continue from any
completed output even when the overall chain failed.

## Model adapter boundary

```pseudo
interface ModelAdapter:
    list_models() -> List<ModelDescriptor>
    generate(model, context) -> GenerationResult
    cancel_if_supported(turn_id)

record GenerationResult:
    content: String

RULE:
    adapters return text
    adapters do not persist conversations
    adapters do not create branches
    adapters do not select the next model
```

## Queries and projections

```text
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}
GET /api/v1/branches/{branch_id}
GET /api/v1/turns/{turn_id}
GET /api/v1/models
GET /api/v1/events?after={cursor}
```

```pseudo
record ConversationProjection:
    conversation
    branches: List<BranchSummary>
    selected_branch: BranchProjection?

record BranchProjection:
    branch
    ancestry: List<BranchSummary>
    messages: List<MessageProjection>
    active_turn: TurnProjection?
    revision: Integer

record TurnProjection:
    turn
    outputs: List<ModelOutput>
```

The projection exposes every model output with its stable `output_id`, allowing
the UI to render a Continue action beside each completed output.

## HTTP command surface

```text
POST /api/v1/conversations
POST /api/v1/conversations/{conversation_id}/turns
POST /api/v1/outputs/{output_id}/continue
POST /api/v1/messages/{message_id}/branch
POST /api/v1/turns/{turn_id}/cancel
```

No generic state-patch endpoint exists.

## UI shape

One screen is sufficient.

```text
+-------------------------------------------------------------------+
| Conversations | Branch path                                      |
|               |---------------------------------------------------|
| conversation  | user message                                     |
| conversation  |                                                   |
|               | model 1 output              [Continue]            |
|               | model 2 output              [Continue]            |
|               | final assistant output      [Continue] [Branch]   |
|               |                                                   |
|               | [message composer]                                |
|               | Mode: Single | Chain                              |
|               | Models: [ordered seat list]                        |
|               |                                      [Send]       |
+-------------------------------------------------------------------+
```

Permitted browser-local state:

```text
unsent draft text
theme
panel dimensions
scroll position
```

Everything else is fetched again after reload.

## Persistence rules

```pseudo
RULE accepted_before_execution:
    persist user message and turn before calling a model

RULE output_before_event:
    persist each model output before announcing completion

RULE immutable_history:
    messages and model outputs are append-only

RULE optimistic_concurrency:
    mutating branch and turn commands carry expected revisions

RULE idempotency:
    repeated command with the same idempotency key creates no duplicate turn

RULE recoverability:
    on backend restart, accepted or running turns are marked recoverable
    executor resumes at first ordinal without a completed output
```

## Minimal database shape

```text
conversations
    id PK, title, root_branch_id, created_at, updated_at, revision

branches
    id PK, conversation_id FK, parent_branch_id FK?,
    forked_from_output_id FK?, forked_from_message_id FK?,
    kind, created_at, revision

messages
    id PK, conversation_id FK, branch_id FK, parent_message_id FK?,
    role, content, created_at

turns
    id PK, conversation_id FK, branch_id FK, user_message_id FK,
    plan_json, status, current_step, final_assistant_message_id FK?,
    error, created_at, updated_at, revision

model_outputs
    id PK, turn_id FK, ordinal, provider, model, content,
    status, error, created_at,
    UNIQUE(turn_id, ordinal)

idempotency_keys
    key PK, command_type, result_json, created_at
```

SQLite is sufficient for the salvage build. The transaction boundary matters
more than the database brand.

## Required acceptance tests

```pseudo
test single_model_turn:
    send one-model plan
    one output is stored
    final assistant message equals that output

test ordered_chain:
    send three-model plan
    outputs have ordinals 0, 1, 2
    each later adapter receives earlier outputs in order
    final assistant message equals output 2

test durable_reload:
    complete turn
    restart backend
    conversation projection is identical

test continue_from_any_output:
    complete three-model chain
    continue separately from outputs 0, 1, and 2
    three child branches are created from the correct contents

test continue_after_chain_failure:
    first model completes and second fails
    first output remains available for Continue

test branch_from_earlier_message:
    branch from an earlier message
    child sees ancestry through fork point
    child does not see later parent or sibling messages

test browser_loss:
    accept turn
    close UI
    backend completes turn
    reopened UI fetches completed projection

test backend_loss:
    stop backend
    UI renders no cached conversation state

test idempotent_send:
    submit identical SendTurn command twice with one idempotency key
    exactly one user message and one turn exist

test execution_recovery:
    persist output 0 of a three-step chain
    restart backend
    execution resumes at output 1 without repeating output 0
```

## Salvage rule

Existing Clearbox code is retained only when it directly implements one of
these responsibilities:

```text
conversation persistence
branch topology
single-model generation
ordered chain generation
model output persistence
Continue from output
branch from message
backend projection
```

Everything else is excluded from the Chat-Chain salvage boundary.
