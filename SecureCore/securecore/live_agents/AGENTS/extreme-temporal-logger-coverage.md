# Extreme Temporal Logger Coverage List

Purpose: define the monitoring surface for a high-security temporal logger where every meaningful movement is recorded with time, source, actor, target, before/after state, and trust context.

Principle: if it moves, changes, appears, disappears, connects, executes, writes, reads sensitive state, escalates, or fails security checks, it gets logged.

## Security Posture

- Default mode is observe-only.
- The logger must not mutate firewall rules, services, tasks, registry keys, files, evidence, agent catalogs, substrates, or runtime state.
- Any future response action must be a separate agent with explicit human approval.
- The logger writes only append-only event records and its own health metadata.
- Event records are immutable after write; corrections are new events that reference the original event ID.
- Clock source, monotonic counter, and ingestion timestamp must all be captured.
- Every event must include collection source, confidence, and whether the event came from direct observation, snapshot diff, or derived correlation.
- Any collection failure is itself a security event.
- Any logging gap, dropped event, queue overflow, or clock rollback is a high-priority event.
- Logs must never include raw secrets; secret-shaped values are redacted and the redaction is logged.

## Core Event Schema

Each logged event should include:

- `event_id`: deterministic or UUID event identifier.
- `event_time_utc`: UTC timestamp from the observed event when available.
- `ingest_time_utc`: UTC timestamp when the logger recorded it.
- `monotonic_sequence`: local monotonic counter for ordering.
- `event_type`: normalized event category.
- `source_sensor`: collector or substrate that observed the event.
- `host_id`: host fingerprint.
- `user_sid`: Windows SID when available.
- `user_name`: account name when safe to record.
- `session_id`: local session identifier when available.
- `process_id`: owning process ID when available.
- `process_name`: owning process name when available.
- `process_path`: normalized executable path when available.
- `parent_process_id`: parent PID when available.
- `parent_process_name`: parent process name when available.
- `command_line_hash`: hash of command line.
- `command_line_redacted`: redacted command line when needed for investigation.
- `object_type`: file, process, network, registry, service, task, agent, substrate, credential, device, or policy.
- `object_id`: normalized target identity.
- `object_path`: file, registry, URL, named pipe, socket, service name, task path, or agent ID.
- `action`: create, read, write, modify, delete, execute, connect, bind, listen, load, unload, start, stop, approve, deny, fail, or drift.
- `before_hash`: pre-change hash when available.
- `after_hash`: post-change hash when available.
- `before_state`: compact pre-change state when available.
- `after_state`: compact post-change state when available.
- `risk_score`: logger-assigned 0-5 risk score.
- `approval_state`: not_required, required, approved, denied, expired, or bypass_attempted.
- `correlation_id`: ID tying related events together.
- `evidence_ref`: pointer to richer evidence artifact when captured.
- `redaction_applied`: true or false.
- `collection_confidence`: high, medium, low, or unknown.
- `integrity_status`: signed, hash_chained, pending, or failed.

## File System Movement

Log these file events:

- File created.
- File opened for write.
- File modified.
- File truncated.
- File overwritten.
- File deleted.
- File renamed.
- File moved between directories.
- File copied into a watched location.
- File copied out of a watched location.
- File metadata changed.
- File owner changed.
- File ACL changed.
- File alternate data stream created or modified.
- File hidden/system attribute changed.
- File extension changed.
- File content hash changed while path stayed stable.
- File path stayed stable while inode/file ID changed.
- Directory created.
- Directory deleted.
- Directory renamed.
- Directory ACL changed.
- Symbolic link, hard link, junction, or mount point created.
- Archive created.
- Archive extracted.
- Executable dropped.
- Script dropped.
- DLL dropped.
- Driver dropped.
- Shortcut created or modified.
- Office macro document created or modified.
- Browser extension file created or modified.
- Evidence file created.
- Evidence file modified.
- Evidence file deleted.
- Log file created.
- Log file modified.
- Log file deleted.

Priority watched paths:

- SecureCore repo root.
- `securecore/live_agents`.
- `securecore/agents`.
- `securecore/substrates`.
- `securecore/data/runtime`.
- `securecore/data/runtime/control_bus`.
- `securecore/data/runtime/evidence`.
- `securecore/data/runtime/logs`.
- `securecore/help/content`.
- `securecore/permissions`.
- `tests`.
- `.git`.
- `.github`.
- User startup folders.
- ProgramData startup folder.
- PowerShell profile paths.
- Windows Task Scheduler storage paths.
- Windows service binary paths.
- Temp directories.
- Downloads directories.
- Public user directories.
- Browser extension directories.
- SSH key directories.
- Credential or token cache directories.

## Process Movement

Log these process events:

- Process start.
- Process exit.
- Process crash.
- Parent-child process relationship.
- Command line observed.
- Command line changed or becomes unavailable.
- Executable path missing.
- Executable hash unknown.
- Executable hash changed from known baseline.
- Process launched from temp path.
- Process launched from user-writable path.
- Process launched from network path.
- Process launched from archive extraction path.
- Process launched as elevated.
- Process token privilege changed.
- Process integrity level changed.
- Process impersonation observed.
- Process injection indicators.
- DLL loaded.
- DLL loaded from user-writable path.
- Unsigned DLL loaded into sensitive process.
- Driver loaded.
- Script interpreter launched.
- Shell launched by office/browser/pdf process.
- PowerShell launched.
- PowerShell encoded command observed.
- PowerShell remote session observed.
- `cmd.exe` launched.
- `wscript.exe` or `cscript.exe` launched.
- `mshta.exe` launched.
- `rundll32.exe` launched.
- `regsvr32.exe` launched.
- `bitsadmin.exe` launched.
- `certutil.exe` launched.
- `schtasks.exe` launched.
- `netsh.exe` launched.
- `sc.exe` launched.
- `wevtutil.exe` launched.
- `vssadmin.exe` launched.
- `bcdedit.exe` launched.
- `curl.exe` or `wget.exe` launched.
- Python, Node, Ruby, Perl, or Java launched with script path.
- SecureCore CLI command launched.
- SecureCore agent runner launched.
- Any process touching evidence paths.
- Any process touching live-agent paths.
- Any process touching firewall, service, task, registry, or audit policy controls.

## Network Movement

Log these network events:

- TCP listener created.
- TCP listener closed.
- UDP endpoint created.
- UDP endpoint closed.
- Outbound TCP connection opened.
- Outbound UDP flow observed.
- Inbound connection accepted.
- Connection state changed.
- Remote address changed.
- Remote DNS name resolved.
- DNS query observed.
- DNS cache entry added.
- DNS cache entry removed.
- DNS cache entry changed.
- Connection to new ASN.
- Connection to new country.
- Connection to known Meta/Facebook ranges.
- Connection to `57.144.174.141`.
- Connection to Tor, proxy, VPN, or anonymizer infrastructure.
- Connection from a process without path.
- Connection from unsigned or unknown process.
- Connection from service host with ambiguous service mapping.
- Localhost listener created.
- Localhost port owner changed.
- Port `11021` listener state changed.
- HTTP.sys URL reservation added.
- HTTP.sys URL reservation removed.
- HTTP.sys service state changed.
- Named pipe server created.
- Named pipe client connected.
- SMB session created.
- RDP session started.
- WinRM session started.
- SSH session started.
- ICMP burst observed.
- Firewall rule created.
- Firewall rule modified.
- Firewall rule deleted.
- Firewall profile changed.
- DNS server configuration changed.
- Proxy configuration changed.
- Hosts file changed.
- Route table changed.
- Network adapter enabled or disabled.
- MAC address changed.
- VPN adapter created or connected.

## Registry Movement

Log these registry events:

- Run key created.
- Run key modified.
- Run key deleted.
- RunOnce key created.
- RunOnce key modified.
- RunOnce key deleted.
- Service registry key created.
- Service registry key modified.
- Driver registry key created or modified.
- Winlogon shell/userinit changed.
- Image File Execution Options changed.
- AppInit DLLs changed.
- KnownDLLs changed.
- LSA provider changed.
- Security package changed.
- WMI persistence key changed.
- PowerShell policy changed.
- Defender policy changed.
- Firewall policy changed.
- Audit policy changed.
- UAC policy changed.
- Remote desktop policy changed.
- AutoLogon setting changed.
- Browser policy changed.
- File association changed.
- Protocol handler changed.
- COM hijack-relevant key changed.
- Scheduled task registry cache changed.
- Certificate store changed.
- Trusted root certificate added or removed.
- Credential provider changed.

## Service And Scheduled Task Movement

Log these service events:

- Service created.
- Service deleted.
- Service started.
- Service stopped.
- Service paused.
- Service restart observed.
- Service start mode changed.
- Service binary path changed.
- Service account changed.
- Service description changed.
- Service recovery action changed.
- Service DLL changed.
- Driver service created.
- Driver service started.
- Unsigned service binary detected.
- Service binary hash changed.
- Service path points to user-writable location.
- SecureCore service registration changed.
- L-Connect service state changed.

Log these scheduled task events:

- Task created.
- Task deleted.
- Task enabled.
- Task disabled.
- Task trigger changed.
- Task action changed.
- Task principal changed.
- Task hidden flag changed.
- Task run result changed.
- Task launched script interpreter.
- Task launched from user-writable path.
- Task launched SecureCore scripts.
- Task launched firewall or registry tooling.

## Identity And Session Movement

Log these identity events:

- Local login success.
- Local login failure.
- Remote login success.
- Remote login failure.
- Unlock event.
- Lock event.
- Logoff event.
- User created.
- User deleted.
- User enabled.
- User disabled.
- User password changed.
- User group membership changed.
- Administrator group membership changed.
- Service account login observed.
- Token elevation observed.
- Privileged operation performed.
- Credential prompt observed when available.
- Credential store changed.
- DPAPI master key changed.
- SSH key created, modified, or deleted.
- API key file created, modified, or deleted.
- Environment variable containing secret-shaped value set.

## SecureCore Agent Movement

Log these SecureCore-specific events:

- Agent catalog file created.
- Agent catalog file modified.
- Agent catalog file deleted.
- Agent JSON spec created.
- Agent JSON spec modified.
- Agent JSON spec deleted.
- Agent runner executed.
- Agent dry-run executed.
- Agent approval phrase accepted.
- Agent approval phrase rejected.
- Agent approval phrase expired.
- Agent attempted execution without approval.
- Restricted agent attempted execution.
- Firewall enforcer attempted execution.
- Snapshot agent attempted execution.
- Live-agent package changed.
- Agent promoted from live lane into runtime lane.
- Agent removed from live lane.
- Agent contract changed.
- Agent risk score changed.
- Agent sandbox requirement changed.
- Agent source file changed.
- Agent output directory changed.
- Agent wrote runtime evidence.
- Agent test file changed.
- Agent test result changed.
- Agent dependency changed.
- Runtime registration changed.
- Application factory registration changed.
- Permission registry changed.
- Approval gate code changed.

## SecureCore Substrate Movement

Log these substrate events:

- Evidence substrate write.
- Evidence substrate read by unusual actor.
- Evidence substrate delete attempt.
- HID substrate event.
- Operator substrate event.
- Telemetry substrate event.
- Ingress substrate event.
- Mirror substrate event.
- Agent decision emitted.
- Command bus message created.
- Command bus message consumed.
- Command bus message failed.
- Control bus heartbeat changed.
- Reaper action proposed.
- Reaper action executed.
- Shun action proposed.
- Shun action executed.
- Decoy content changed.
- Decoy route touched.
- Help content changed.
- LLM context changed.
- Permission gate decision changed.
- Validator confidence result changed.
- Forge record appended.
- WAL entry appended.
- WAL integrity failure.

## Git And Repository Movement

Log these git/repo events:

- Git commit created.
- Git branch created.
- Git branch switched.
- Git branch deleted.
- Git tag created.
- Git remote changed.
- Git fetch performed.
- Git pull performed.
- Git push performed.
- Git merge performed.
- Git rebase performed.
- Git reset attempted.
- Git checkout of file attempted.
- Git stash created or applied.
- `.git/config` changed.
- `.git/hooks` changed.
- Working tree dirty state changed.
- Security-relevant file staged.
- Security-relevant file unstaged.
- Live-agent file staged.
- Live-agent file committed.
- Test file committed.
- CI workflow changed.
- Dependency lockfile changed.

## Evidence And Audit Integrity

Log these integrity events:

- Log segment opened.
- Log segment closed.
- Log segment hash chained.
- Log segment signature created.
- Log segment upload attempted.
- Log segment upload succeeded.
- Log segment upload failed.
- Log segment read.
- Log retention policy changed.
- Log compaction attempted.
- Log deletion attempted.
- Event schema version changed.
- Redaction rule changed.
- Sensor enabled.
- Sensor disabled.
- Sensor crashed.
- Sensor restarted.
- Sensor fell behind.
- Sensor queue overflow.
- Sensor dropped event.
- Sensor duplicate event detected.
- Clock jumped forward.
- Clock jumped backward.
- Time source changed.
- Monotonic counter reset.
- Host fingerprint changed.
- Baseline created.
- Baseline changed.
- Baseline mismatch detected.

## Security Control Movement

Log these security-control events:

- Windows Defender setting changed.
- Defender exclusion added.
- Defender exclusion removed.
- Real-time protection changed.
- Tamper protection state changed.
- Firewall enabled or disabled.
- Firewall rule added.
- Firewall rule modified.
- Firewall rule removed.
- Firewall profile changed.
- Audit policy changed.
- Event log cleared.
- Event log service stopped.
- Sysmon configuration changed.
- ETW provider disabled.
- PowerShell logging policy changed.
- Script block logging changed.
- Module logging changed.
- Transcription logging changed.
- AMSI bypass indicator observed.
- UAC setting changed.
- BitLocker state changed.
- Secure Boot state changed.
- Certificate trust store changed.

## Browser And User Surface Movement

Log these browser/user-surface events:

- Browser process started.
- Browser extension installed.
- Browser extension removed.
- Browser extension updated.
- Browser profile file changed.
- Browser download created.
- Browser download executed.
- Browser password store changed.
- Browser cookie store changed.
- Browser proxy changed.
- Clipboard write observed where available.
- Clipboard contains secret-shaped value where available.
- Screen capture process started.
- Keyboard/mouse collector state changed.
- Remote assistance started.
- New desktop session created.

## Alert Priority Rules

Immediate alert:

- Any approval bypass attempt.
- Any restricted agent execution attempt.
- Any firewall mutation.
- Any event log clear.
- Any Defender exclusion add.
- Any SecureCore live-agent contract or runner mutation.
- Any evidence deletion or modification.
- Any process from temp path touching SecureCore or evidence.
- Any unsigned process modifying persistence.
- Any clock rollback.
- Any logging sensor disabled.

High priority:

- New listener.
- New scheduled task.
- New service.
- New Run key.
- New admin group member.
- New trusted root certificate.
- New outbound connection by unknown process.
- New PowerShell encoded command.
- New HTTP.sys URL reservation.
- New file in startup path.
- Git reset, rebase, or force push.

Medium priority:

- Process start from user-writable path.
- DNS cache change for unusual domain.
- Browser extension update.
- Dependency file change.
- Agent dry-run of restricted action.
- Service restart.

Low priority:

- Expected SecureCore test execution.
- Expected report-only snapshot after approval.
- Known vendor service heartbeat.
- Known localhost-only service connection with stable owner.

## Noise Controls Without Blind Spots

- Suppress only by exact actor, path, hash, action, and time window.
- Never suppress security-control changes.
- Never suppress evidence path changes.
- Never suppress live-agent path changes.
- Never suppress approval events.
- Never suppress logging health events.
- Suppression creation, modification, and expiration are logged.
- Every suppressed event increments a visible counter.

## Minimum Watched Sources

- File system watcher for SecureCore repo and security-sensitive host paths.
- Periodic full snapshot diff for files where watcher events can be missed.
- Process creation/exit feed.
- Network connection snapshot diff.
- DNS cache snapshot diff.
- Registry watcher for persistence and security policy keys.
- Service snapshot diff.
- Scheduled task snapshot diff.
- Windows event log collector.
- Git status/log watcher for SecureCore repo.
- SecureCore command bus hook.
- SecureCore permission gate hook.
- SecureCore agent runner hook.
- SecureCore evidence writer hook.
- Logger self-health heartbeat.

## Approval Requirements

The temporal logger itself should require no approval for observation and append-only logging.

Human approval is required before any linked agent:

- Blocks a network address.
- Changes firewall rules.
- Stops a process.
- Kills a process.
- Disables a service.
- Deletes a task.
- Deletes a file.
- Quarantines a file.
- Modifies registry keys.
- Changes SecureCore agent catalogs.
- Promotes a live agent.
- Alters evidence retention.
- Alters logger redaction or suppression rules.

## Deliverable Checklist For Implementation

- Define event schema as code.
- Define watched source registry.
- Define risk scoring rules.
- Define append-only event writer.
- Define redaction rules.
- Define hash-chain integrity.
- Define snapshot diff collectors.
- Define live event collectors.
- Define SecureCore hook points.
- Define approval event ingestion.
- Define suppression ledger.
- Define health heartbeat.
- Define tests proving no mutation outside log output.
- Define tests proving sensitive paths are watched.
- Define tests proving approval bypass attempts are logged.
- Define tests proving logger failures are logged.
- Define tests proving event schema is stable.
