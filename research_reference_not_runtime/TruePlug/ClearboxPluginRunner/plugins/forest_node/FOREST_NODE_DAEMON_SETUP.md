# Forest Node Daemon — Setup Guide

**Version 0.5.0** | One file, any Windows machine, 2-minute setup.

---

## What This Is

The Forest Node daemon turns any Windows PC into a node that your main
Forest AI installation can reach over LAN. Once paired, the controller
can browse files, upload, create folders, and delete — all gated behind
a 4-layer security model you control from both ends.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| Python | 3.10+ |
| Packages | `fastapi`, `uvicorn` |
| OS | Windows 10/11 (Linux works for reads; junction detection is Windows-only) |

```
pip install fastapi uvicorn
```

---

## Quick Start

### 1. Copy the file

Copy **`node_daemon_standalone.py`** to the remote machine. That's the
only file you need — no plugins, no config files, no database.

### 2. Run it

```
python node_daemon_standalone.py
```

First run prints a **pairing key** — a 64-character hex string:

```
  *** NEW PAIRING KEY ***
  a1b2c3d4e5f6...  (64 hex chars)
  Copy this key to the controller. It will not be shown again.
  Use --print-pairing-key to display it later.
```

**Write this key down.** You'll enter it on the controller to pair.

### 3. Register on the controller

In Forest AI (the controller), open **Nodes** and click **Add Node**.
Enter the remote machine's IP and port (default `5052`). The controller
probes `/node/health` and `/node/caps` — if the daemon is reachable
it shows up in the node list.

### 4. Pair

Click **Pair** on the registered node. Paste the 64-char hex key.
The controller verifies it against the daemon via challenge/response.
Once paired, file access and write operations become available.

---

## CLI Flags

| Flag | What it does |
|------|-------------|
| `--port 5052` | Listen port (default: `5052`) |
| `--host 0.0.0.0` | Bind address (default: `0.0.0.0` = all interfaces) |
| `--allow-full` | Allow FULL read mode (entire filesystem). Without this, only allowlist dirs are accessible. |
| `--print-pairing-key` | Print the current pairing key and exit |
| `--generate-pairing-key` | Generate a new key (invalidates all existing sessions) |
| `--pairing-key-file PATH` | Custom key file location (default: `./pairing_secret.key` next to the script) |

### Examples

```bash
# Default — allowlist dirs only, port 5052
python node_daemon_standalone.py

# Custom port, allow full-system reads
python node_daemon_standalone.py --port 6000 --allow-full

# Show the existing pairing key (doesn't start the daemon)
python node_daemon_standalone.py --print-pairing-key

# Force a new pairing key (old key stops working immediately)
python node_daemon_standalone.py --generate-pairing-key
```

---

## Environment Variables

All optional. CLI flags override where applicable.

| Variable | Default | What it does |
|----------|---------|-------------|
| `PORT` | `5052` | Listen port (same as `--port`) |
| `ALLOWED_ROOTS` | `~/Documents,~/Desktop,~/Downloads` | Comma-separated directories for allowlist mode |
| `MAX_READ_SIZE` | `104857600` (100 MB) | Max file size for reads |
| `MAX_WRITE_SIZE` | `10485760` (10 MB) | Max file size for writes/uploads |

### Custom allowlist example

```bash
set ALLOWED_ROOTS=C:\Projects,D:\SharedData
python node_daemon_standalone.py
```

---

## Security Model (4 Layers)

Every write operation must pass **all four** gates. Any failure = rejected.

| Layer | Question | Who controls it |
|-------|----------|----------------|
| **1. Windows Hello** | Is the controller operator who they say they are? | Controller (biometric on the machine running Forest AI) |
| **2. HMAC Pairing** | Does the controller have the right secret? | Both (daemon generates key, controller stores it) |
| **3. Access Mode** | Is the daemon open for file access? | Controller requests, daemon enforces. Starts `locked`. |
| **4. share_write** | Did the operator explicitly enable writes? | Controller toggles. Auto-clears when mode returns to `locked`. |

### Access modes

| Mode | Reads | Writes | Scope |
|------|-------|--------|-------|
| `locked` | No | No | Nothing accessible |
| `allowlist` | Yes | If `share_write` on | Only dirs in `ALLOWED_ROOTS` |
| `full` | Yes | If `share_write` on | Entire filesystem (requires `--allow-full` on startup) |

- Mode starts **locked** every time the daemon boots.
- The controller can switch to `allowlist` or `full` via the UI.
- `full` mode is only available if the daemon was started with `--allow-full`.
- `share_write` is a separate toggle — you can browse files (read) without
  enabling writes. Writes require an explicit click in the UI.
- Locking the mode **auto-clears** `share_write`. No writes persist
  across a lock transition.

---

## Endpoints Reference

### Public (no auth)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/node/hello` | Liveness check — returns node_id, version, uptime |
| GET | `/node/health` | Heartbeat probe — used by controller |
| GET | `/node/caps` | Hardware capabilities (CPU, RAM, GPU, disk) |

### Auth (pairing required, no session)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/node/auth/challenge` | Get a single-use nonce |
| POST | `/node/auth/session` | Submit HMAC response, receive session token |

### File access (session token required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/node/fs/mode` | Current access mode state |
| POST | `/node/fs/mode` | Set access mode + write flag |
| GET | `/node/fs/list?path=...` | List directory contents |
| GET | `/node/fs/stat?path=...` | Stat a single file/directory |
| GET | `/node/fs/read?path=...` | Stream file bytes (up to 100 MB) |
| POST | `/node/fs/write` | Write/overwrite a file (base64, up to 10 MB) |
| POST | `/node/fs/mkdir` | Create a directory |
| POST | `/node/fs/delete` | Delete a file or empty directory |

---

## Firewall

The daemon listens on TCP port `5052` (or your custom `--port`).
The controller needs to reach this port over LAN.

**Windows Firewall** — if the controller can't connect, allow the port:

```
netsh advfirewall firewall add rule name="Forest Node" dir=in action=allow protocol=tcp localport=5052
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Controller can't find the node | Check firewall, verify IP:port, confirm daemon is running |
| "No pairing key configured" | Daemon started without a key file. Restart normally — it auto-generates. |
| Pairing rejected | Wrong key. Use `--print-pairing-key` on the daemon to check. |
| "Write access is disabled" | `share_write` is off. Toggle Write ON in the file browser toolbar. |
| "Path outside allowed roots" | File is outside the allowlist dirs. Either add the dir to `ALLOWED_ROOTS` or start with `--allow-full`. |
| "File too large" (413) | File exceeds `MAX_WRITE_SIZE` (10 MB default). Increase via env var if needed. |
| "FULL mode requires --allow-full" | Restart the daemon with the `--allow-full` flag. |
| Session expired | Automatic — controller re-authenticates on next request. If persistent, re-pair. |

---

## File Layout (on the daemon machine)

```
node_daemon_standalone.py     ← the daemon (only file you copy)
pairing_secret.key            ← auto-generated on first run (32 bytes, binary)
```

That's it. No database, no config directory, no dependencies beyond
FastAPI + uvicorn.
