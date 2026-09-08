# DocuFilm pause, child accounting, and return

Implemented entrypoints in `truevision_intake.document_state.intake_control`:

- `IntakeControl(path, run_id=..., policy=...)`: single-writer persistent
  mark journal; validates hashes, custody context and legal transitions on reopen.
- `intake_state_movie(manifest_path, journal_path, run_id=..., reader=...,
  max_positions=None)`: existing stored-state connected-component detection
  and `DocumentStateReader` intake, with per-frame pause and child accounting.

The state-movie adapter does not open a camera, discover semantic insets,
decode audio, or admit objects to TrueMem. It consumes an existing state movie.
Detection means connected dark-cell components at luma threshold 128, not
semantic object recognition. Unknown glyphs remain unknown.

## Marks and enforcement

`START -> DETECTION_STARTED -> DETECTION_ENDED -> PARENT_PAUSED ->
CHILD_STARTED -> CHILD_ENDED -> RETURN_TO_PARENT_PAUSE -> PARENT_RESUMED`.
Each parent may contain multiple children. Children can use the same nested
sequence through the controller API. `FINISH` requires a running root and
an exact consumed-position count.

Marks carry a sequence, hash-chain link, object/parent/source identity and
position context, and a pre-transition state hash. Detection-end lists the
child inventory and its detection-start mark. Child-end binds its start mark
and preserves the result or explicit failure. Return binds the saved pause
mark/state and requires every detected child to be accounted for.

`require_success` blocks return after failed/cancelled/unresolved children.
`account_all` permits return with those outcomes recorded; it does not turn
them into successes. `CHILD_RETRY` requires a failed child and explicit reason;
previous failure marks remain in the journal. No automatic effectful retry.

The state-movie adapter always uses `require_success`. A reader exception
records a failed child and returns `BLOCKED`. `max_positions` returns `PAUSED`
between frames. Reopening continues from the saved cursor, binding the source
manifest, chunk hashes, lexicon and lifetime-count configuration. Interrupted
read-only child reads may repeat, but already completed children are not repeated.
Successful termination returns `COMPLETE`. Intake completion does not establish
recognition accuracy.

## Persistence and limits

Checkpoints use a flushed/fsynced temporary file, atomic replace and directory
fsync. A leftover `.pending` file fails closed; recovery from a power loss during
publication is not automated. This is a single-writer API, not a concurrent job
queue. Hash integrity is not authentication against someone rewriting the whole
journal. Journal snapshots are rewritten per mark; large-run optimization is
not qualified. No gradient training, model changes or generated pictures occur.

External qualification:
`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/test_docufilm_control.py`.
Run with `python -B`. Tests include nested marks, invalid transitions, failures,
retry, hash tampering, real state extraction from a pre-existing derived
30-second video, interruption/reopen, and deterministic journal equivalence.
