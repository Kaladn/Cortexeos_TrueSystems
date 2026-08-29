# Source provenance

| Combined directory | Canonical source directory |
| --- | --- |
| `TrueCore/` | Pre-rename canonical security source retained locally; renamed in this combined repository |
| `TrueMachine/` | `/home/lamercey/TrueMachine` |
| `TrueVision/` | GitHub `Kaladn/TrueVision-Video-Rendering` at `e5ac3a41de6dbd5c025aae290603c864046ffc8e`; verified against `/home/lamercey/TrueVision_Codebase_Clean_Linux` |
| `TrueAudio/` | Extracted from canonical TrueVision, then ported to Linux PipeWire/Pulse monitor capture without raw-audio persistence |
| `TrueSpeech/` | Extracted from canonical TrueVision and wired to the top-level TrueAudio package |
| `TrueVisionIntake/` | Extracted from canonical TrueVision DocuFilm/document-state intake and made the single top-level intake owner |
| `TrueMem/` | Pre-rename mounted source directory plus current combined-repository corrections; prior path remains recoverable from repository history |
| `LocalMemoryChat/` | Mounted local source directory recorded by the original assembly commit |
| `clearbox-chat-chain/` | `/home/lamercey/clearbox-chat-chain` |

The assembly began from those source trees, then applied the recorded TrueCore,
TrueMem, Linux, and unnesting changes in this repository. It did not copy nested
repository metadata or runtime/generated state.
