# Host-reviewed response publication

`truecore.response_gate.ResponseGate.publish` accepts exactly conversation ID,
turn ID, context SHA-256 and text. It returns no text unless the hash of that
exact proposal appears in an out-of-band host approval set. Extra model fields,
changed text, changed context/turn, malformed and oversized proposals cannot
reuse an approval. No partial model streaming is exposed by this interface.

This is an exact-approval gate, not an automatic semantic safety classifier,
factual validator, or OS sandbox. The host/reviewer is trusted. Do not put
approval files or host command execution in the model's tool surface.

The host CLI is `python -m truecore.response_gate --proposal FILE
--host-approvals FILE`. The approvals file is a JSON list of reviewed proposal
hashes. An empty list withholds all model prose. It performs no tool action.

The professional-model offline evaluator calls this gate with no approvals;
raw generations remain private review artifacts, not chat responses. No public
chat service was deployed. Existing `ModelHost` remains the sole action-request
transport to the five existing read-only operations. This gate does not add a
generation operation or qualify any agent backend.
