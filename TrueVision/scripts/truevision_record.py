#!/usr/bin/env python3
"""Record native visual state with the historical clarity grid and safe disk stop."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

DEFAULT_DRIVE = Path('/run/media/lamercey/New Volume')
DEFAULT_BINARY = Path('/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/output/native-repair-build-20260908/release/truevision_capture_rs')

def command(binary, root, hours):
    return [str(binary), '--duration', str(hours * 3600 if hours else 1e12), '--fps', '9',
            '--resolution', '2560x1440', '--grid', '640x360',
            '--cell-chunk-frames', '9', '--output-root', str(root),
            '--run-id', 'observation', '--stop-file', str(root / 'STOP')]

def seal(root, result):
    """Seal a stopped run, including failed runs; never claim semantic completeness."""
    (root/'result.json').write_text(json.dumps(result, indent=2))
    with (root/'sha256.jsonl').open('x') as ledger:
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.name != 'sha256.jsonl':
                with path.open('rb') as f:
                    digest = hashlib.file_digest(f, 'sha256').hexdigest()
                ledger.write(json.dumps({'path': str(path.relative_to(root)),
                    'sha256': digest, 'bytes': path.stat().st_size})+'\n')
        ledger.flush()
        os.fsync(ledger.fileno())
    with (root/'sha256.jsonl').open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    receipt = {'schema': 'truevision_run_seal@1', 'sealed_at': datetime.now(timezone.utc).isoformat(),
        'ledger_sha256': digest, 'native_exit': result['native_exit'],
        'status': 'SEALED' if result['native_exit'] == 0 and result['manifest_present'] else 'SEALED_FAILED',
        'scope': 'hash inventory of stopped run; not proof of visual fidelity or complete source capture'}
    pending = root/'seal.pending'
    with pending.open('x') as f:
        json.dump(receipt, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    pending.replace(root/'SEALED.json')

def announce(message):
    try:
        print(message, flush=True)
    except OSError:
        pass  # Terminal closure must not interrupt sealing.

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hours', type=float, default=0, help='Optional time limit; default continues until Ctrl+C or disk safety stop')
    p.add_argument('--drive', type=Path, default=DEFAULT_DRIVE)
    p.add_argument('--binary', type=Path, default=DEFAULT_BINARY)
    p.add_argument('--reserve-gib', type=float, default=50)
    p.add_argument('--check', action='store_true', help='Show readiness without recording')
    a = p.parse_args()
    if not 0 <= a.hours <= 168 or a.reserve_gib < 10:
        p.error('hours must be >=0 and <=168; reserve must be >=10 GiB')
    drive = a.drive.resolve()
    if not drive.is_mount() or os.stat(drive).st_dev == os.stat('/').st_dev:
        p.error('drive must be a mounted non-system filesystem; refusing root-disk fallback')
    if not a.binary.is_file():
        p.error('native binary is missing')
    free = shutil.disk_usage(drive).free
    reserve = a.reserve_gib * 1024**3
    if free < reserve + 1024**3:
        p.error('insufficient free space above reserve')
    rate = 640 * 360 * 16 * 4 * 9
    print(json.dumps({'drive': str(drive), 'free_bytes': free,
        'nominal_state_bytes_per_second': rate,
        'estimated_hours_before_disk_stop': (free-reserve)/rate/3600,
        'grid': '640x360', 'fps': 9, 'raw_video_saved': False}, indent=2), flush=True)
    if a.check:
        return
    root = drive / 'TrueVision-Logs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root.mkdir(parents=True, exist_ok=False)
    stop = root / 'STOP'
    reason = {'value': 'duration_completed'}
    def request_stop(signum, frame):
        reason['value'] = 'operator_stop'
        stop.touch()
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGHUP, request_stop)
    cmd = command(a.binary, root, a.hours)
    with a.binary.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    (root/'plan.json').write_text(json.dumps({'command': cmd, 'binary_sha256': digest,
        'disk_reserve_bytes': reserve, 'observation_only': True}, indent=2))
    announce(f'TrueVision logging: {root}\nApprove the monitor chooser. Ctrl+C stops and flushes state.')
    started = time.monotonic()
    with (root/'native.stdout.log').open('w') as out, (root/'native.stderr.log').open('w') as err:
        child = subprocess.Popen(cmd, stdout=out, stderr=err, start_new_session=True)
        while child.poll() is None:
            free = shutil.disk_usage(drive).free
            if free < reserve and not stop.exists():
                reason['value'] = 'disk_reserve_reached'
                stop.touch()
            status = {'pid': child.pid, 'elapsed_seconds': time.monotonic()-started,
                      'free_bytes': free, 'stop_requested': stop.exists()}
            pending = root/'status.pending'
            pending.write_text(json.dumps(status))
            pending.replace(root/'status.json')
            time.sleep(1)
    manifest = root/'observation/observation_manifest.json'
    result = {'native_exit': child.returncode, 'stop_reason': reason['value'],
              'manifest_present': manifest.exists(), 'wall_seconds': time.monotonic()-started}
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_IGN)
    seal(root, result)
    announce(json.dumps(result, indent=2))
    if child.returncode or not manifest.exists():
        raise SystemExit(1)

if __name__ == '__main__':
    main()
