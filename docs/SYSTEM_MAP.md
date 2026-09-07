# Current code map

| Boundary | Code entrypoint | Reads | Writes or returns |
| --- | --- | --- | --- |
| TrueMachine | `TrueMachine/src/truemachine/cli.py` | Linux identity, memory, process, network, explicit state artifacts | WAL, index, current Fusion Pack, verification JSON |
| TrueVision Intake / DocuFilm | `TrueVisionIntake/truevision_intake/document_state/` | document page state, glyph-state records, and frozen code-deciphering context | authoritative document-state reads, fail-closed visual code reads, and parent/contained intake records |
| TrueAudio | `TrueAudio/trueaudio_runtime/` | decoded file audio or Linux PipeWire default-output monitor | deterministic derived audio state, replayable state, manifests, receipts |
| TrueSpeech | `TrueSpeech/truespeech_runtime/` | replayable TrueAudio state and optional caller-supplied lyrics | speech-region and lyric-alignment candidates without transcript claims |
| TrueMem | `TrueMem/src/truemem/cli.py` | DocuFilm-admitted strings and mapped artifacts under one runtime root | opaque symbols, counts, positions, relationships, citations, query and deeper/wider packets; active storage uses workspace-monotonic six-byte symbol ranges |
| LocalMemoryChat | `LocalMemoryChat/src/local_memory_chat/cli.py` | explicit local files, attachments, profile state | cited memory packet and receipts |
| TrueCore | `TrueCore/truecore/cli/main.py` | substrates, Forge, registered runtime state | inspection output; gated decisions/actions through its own runtime |
| Chat-Chain | `clearbox-chat-chain/src/clearbox_chat_chain/server.py` | HTTP chat commands and configured provider results | SQLite WAL conversation state and HTTP results |
| Control API | `control-api/src/truesystems_api/server.py` | localhost JSON requests | delegated results only |
| Help | `control-api/src/truesystems_api/help.py` | current help catalog and source files | read-only answer with resolved citations |

DocuFilm is the sole intake authority; TrueMem does not own a competing intake
boundary. The control API directly wires TrueMachine pulse, TrueMem query/deeper-wider,
LocalMemoryChat ask, Chat-Chain operations, and help. TrueCore remains a
separate organism and is health-probed rather than imported because importing
its application starts runtime behavior.
