# Linux port status

Verified on 2026-08-29:

- TrueAudio uses the Linux PipeWire/Pulse default-output monitor and writes only derived state.
- TrueSpeech consumes the top-level TrueAudio package.
- TrueVision Intake owns DocuFilm and is referenced by TrueVision rather than duplicated.
- TrueVision Python and Rust generation/replay tests pass as a combined suite: 328 tests and 6 subtests.
- TrueVision native capture uses the Wayland ScreenCast portal and its authorized
  PipeWire node. Frames are transient memory only; live acceptance produced only
  `.tvcells`, JSONL, and JSON artifacts with canonical microsecond UTC timestamps.
- TrueVision, TrueMem, TrueCore, and renderer hardware probes no longer execute PowerShell or Win32 memory calls.
- TrueCore callable catalogs contain no WinUtil or recovered PowerShell agents; Windows process names remain only as security evidence signatures.
- TrueCore's declared Python dependencies are locked outside the repository at
  `/home/lamercey/.local/share/truesystems/truecore-venv`; all 253 tests, 11
  subtests, and every isolated test file pass there.
- TrueMem performs zero normalization for admitted anchor identity and symbol
  assignment. Case, Unicode composition, hyphen/dash form, apostrophe form, and
  spelling remain exact. Its combined suite passes 49 tests.
- The external sequential chain passes for every covered component and every
  repository-native test file.

Retained boundaries:

- An explicit TrueVision `--region` request additionally requires GStreamer's
  optional `videocrop` element. Full-monitor capture does not require it.
- Windows executable and PowerShell strings retained in TrueCore are detection
  evidence/signatures, not executable Windows implementations.

Passing tests do not override these stated architectural boundaries.
