Temporal / Log / Reader / Causality Manifest - rg candidate pass + full hash verification
Created: 2026-05-16T10:50:26
Mounted drives scanned: C:\, D:\, E:\, G:\
Unavailable expected drives: F:\ unavailable: [WinError -2144272384] This drive is locked by BitLocker Drive Encryption. You must unlock this drive from Control Panel: 'F:\\', H:\ missing_or_unmounted

Target concepts:
- temporal systems: temporal, timestamp, timeline, chronos, timebase, clock, sequence, replay, snapshot, time series
- temporal logging: log, logger, logging, event log, audit log, runtime log, reasoning log, trace, journal
- readers: log reader, temporal reader, history reader, trace reader, reader/retriever/resolver/parser in target context
- causality: causal, causality, cause/effect, provenance/dependency adjacent files

Verification gate before manifest entry:
- file exists at verification time
- path is a regular file
- size is nonzero
- full SHA-256 read completed to EOF
- bytes read during hash equals current file size
- file size did not change during hash

Files that failed this gate are in SKIPPED_FAILED_VERIFICATION.csv, not the manifest.
Raw candidate paths are stored in RAW_CANDIDATE_PATHS.csv so no terminal-truncated output was used as the manifest source.

Scope pruning:
- Scanned mounted filesystem drives, while pruning OS/vendor/package/cache/build areas such as Windows, Program Files, node_modules, site-packages, virtualenvs, git dirs, Python install libs, VS Code extension/vendor dirs, recycle bin, and prior generated folders.
- Locked/unmounted drives are listed in UNAVAILABLE_DRIVES.txt.
