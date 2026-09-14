"""Finite host-bound jobs, registered execution, and one terminal receipt.

This is an application boundary for explicitly admitted local work, not an OS
sandbox, a general shell, an autonomous code author, or the final system seal.
The operator authors a plan; the host admits its exact digest and authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import uuid

from .live_agents.manifest import load_agent_manifest
from .live_agents.worker_result import build_result, validate_result

CORE = Path(__file__).resolve().parents[1]
ROOT = CORE.parent
AGENTS = CORE / 'truecore/live_agents/AGENTS'
RUNNER = AGENTS / 'runner/truecore_agent_runner.py'
WORKERS = {
    'job_patch_files': 'patch_files',
    'job_acceptance_run': 'acceptance_run',
    'job_history_readiness': 'history_readiness',
    'job_history_order': 'history_order',
    'job_graph_review': 'graph_review',
}
MAX_BYTES = 8_000_000
JOB_ARGUMENTS = {'job_id': {'type': 'string', 'pattern': '[A-Za-z0-9_-]{1,80}',
                            'meaning': 'host-admitted job identity'}}


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, maximum=MAX_BYTES):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('UNSAFE_PATH')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('REGULAR_FILE_REQUIRED')
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('BYTE_BUDGET_EXCEEDED')
    return raw


def atomic(path, raw, mode=0o600):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def check_hashes(bindings):
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('SOURCE_BINDINGS_REQUIRED')
    for binding in bindings:
        if set(binding) != {'path', 'sha256'} or sha(regular(binding['path'])) != binding['sha256']:
            raise ValueError('STALE_OR_CHANGED_SOURCE')


def load_plan(binding):
    if set(binding) != {'plan_path', 'plan_sha256', 'approval_sha256', 'output_root'}:
        raise ValueError('INVALID_HOST_JOB_BINDING')
    raw = regular(binding['plan_path'])
    if sha(raw) != binding['plan_sha256'] or binding['approval_sha256'] != binding['plan_sha256']:
        raise ValueError('JOB_NOT_ADMITTED')
    plan = json.loads(raw)
    if set(plan) != {'schema', 'job_id', 'original_request_sha256', 'steps', 'implementation_bindings'}:
        raise ValueError('INVALID_JOB_PLAN')
    if plan['schema'] != 'truecore.bounded_job_plan@1' or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', plan['job_id']):
        raise ValueError('INVALID_JOB_IDENTITY')
    if not re.fullmatch(r'[0-9a-f]{64}', plan['original_request_sha256']):
        raise ValueError('REQUEST_IDENTITY_REQUIRED')
    steps = plan['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise ValueError('JOB_STEP_BUDGET')
    ids = set()
    for step in steps:
        if not {'step_id', 'worker_id', 'config'} <= set(step) or set(step) - {'step_id', 'worker_id', 'config', 'depends_on'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', step['step_id']):
            raise ValueError('INVALID_JOB_STEP')
        if step['step_id'] in ids or not isinstance(step['config'], dict):
            raise ValueError('INVALID_JOB_STEP')
        dependencies = step.get('depends_on', list(ids))
        if not isinstance(dependencies, list) or any(not isinstance(d, str) or d not in ids for d in dependencies) or len(set(dependencies)) != len(dependencies):
            raise ValueError('INVALID_STEP_DEPENDENCIES')
        ids.add(step['step_id'])
    check_hashes(plan['implementation_bindings'])
    out = Path(binding['output_root'])
    if not out.is_absolute() or not out.is_dir() or any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('INVALID_HOST_OUTPUT_ROOT')
    return plan, out / plan['job_id']


def bounded_process(argv, *, cwd, timeout, maximum, env):
    """Capture a bounded combined stream; kill the whole child group on limits."""
    if type(timeout) is not int or not 1 <= timeout <= 600 or type(maximum) is not int or not 1 <= maximum <= MAX_BYTES:
        raise ValueError('INVALID_PROCESS_BUDGET')
    start = time.monotonic()
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    data = bytearray()
    reason = None
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while selector.get_map():
                if time.monotonic() - start > timeout:
                    reason = 'TIME_BUDGET_EXCEEDED'
                    break
                for key, _ in selector.select(.05):
                    chunk = os.read(key.fileobj.fileno(), min(65536, maximum + 1 - len(data)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        data.extend(chunk)
                if len(data) > maximum:
                    reason = 'OUTPUT_BUDGET_EXCEEDED'
                    break
            if reason:
                os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=max(.1, timeout - (time.monotonic() - start)))
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        finally:
            process.stdout.close()
    return code, bytes(data[:maximum]), reason, round(time.monotonic() - start, 6)


def environment():
    return {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONPATH': os.pathsep.join(str(ROOT / p) for p in
                ('TrueCore', 'TrueMachine/src', 'TrueVision', 'TrueVision/scripts', 'TrueAudio', 'TrueSpeech', 'TrueMem/src', 'TrueVisionIntake/src', 'control-api/src'))}


def invoke_step(binding, step):
    worker = step['worker_id']
    if worker not in WORKERS:
        return build_result(worker_id=worker, operation='job.step', status='NOT_IMPLEMENTED',
            unresolved=[{'code': 'WORKER_NOT_IMPLEMENTED', 'required_worker': worker}],
            continuation='STOP_NOT_IMPLEMENTED', reason_code='WORKER_NOT_IMPLEMENTED')
    manifest_path = AGENTS / 'agents' / f'{worker}.agent.json'
    manifest = load_agent_manifest(manifest_path)
    expected = 'truecore.agents.bounded_job_workers:' + WORKERS[worker]
    source = CORE / 'truecore/agents/bounded_job_workers.py'
    if manifest.get('source_entrypoint') != expected or manifest.get('source_entrypoint_hash') != 'sha256:' + sha(regular(source)):
        raise ValueError('WORKER_IMPLEMENTATION_CHANGED')
    payload = json.dumps({'kwargs': {'binding': binding, 'step_id': step['step_id']}})
    argv = [sys.executable, '-B', str(RUNNER), '--catalog', str(AGENTS / 'catalog/bounded_job_catalog.csv'),
            '--agent-dir', str(AGENTS / 'agents'), 'run', worker, '--param', 'input_json=' + payload]
    if manifest['requires_approval']:
        # Host admission of the exact plan supplies authority; caller cannot set it.
        argv += ['--approve', manifest['approval_phrase']]
    code, raw, reason, elapsed = bounded_process(argv, cwd=CORE, timeout=600, maximum=MAX_BYTES, env=environment())
    if reason or code:
        _, directory = load_plan(binding)
        incident = directory / (step['step_id'] + '.incident.log')
        atomic(incident, raw)
        return build_result(worker_id=worker, operation='job.step', status='FAILED',
            errors=[{'code': reason or 'WORKER_PROCESS_FAILED'}],
            result={'elapsed_seconds': elapsed, 'process_returncode': code},
            artifacts=[{'kind': 'bounded_failure_output', 'path': str(incident), 'sha256': sha(raw)}],
            continuation='STOP_FAILED', reason_code=reason or 'WORKER_PROCESS_FAILED')
    packet = json.loads(raw)
    validate_result(packet)
    if packet['worker_id'] != worker:
        raise ValueError('WORKER_IDENTITY_MISMATCH')
    return packet


def execute_job(binding):
    plan, directory = load_plan(binding)
    terminal = directory / 'job_receipt.json'
    if directory.exists():
        if terminal.is_file():
            return inspect_receipt(terminal, binding['plan_sha256'])
        return build_result(worker_id='bounded_job', operation='job.execute', status='REFUSED',
            unresolved=[{'code': 'INTERRUPTED_JOB_REQUIRES_INSPECTION'}], continuation='STOP_REFUSED',
            reason_code='INTERRUPTED_JOB_REQUIRES_INSPECTION')
    directory.mkdir(mode=0o700)
    start = time.monotonic()
    progress = directory / 'progress.json'
    results = []
    try:
        for step in plan['steps']:
            completed = {r['step_id']: r['worker_result']['status'] for r in results}
            dependencies = step.get('depends_on', list(completed))
            if any(completed.get(name) != 'COMPLETE' for name in dependencies):
                results.append({'step_id': step['step_id'], 'execution': 'not_run',
                    'worker_result': build_result(worker_id=step['worker_id'], operation='job.step', status='UNRESOLVED',
                        unresolved=[{'code': 'DEPENDENCY_NOT_COMPLETE', 'dependencies': dependencies}],
                        continuation='STOP_NO_EVIDENCE', reason_code='DEPENDENCY_NOT_COMPLETE')})
                continue
            atomic(progress, canonical({'plan_sha256': binding['plan_sha256'], 'pending_step': step['step_id'],
                                        'completed_steps': results}))
            packet = invoke_step(binding, step)
            results.append({'step_id': step['step_id'], 'execution': 'worker_invoked', 'worker_result': packet})
            if packet['status'] in {'FAILED', 'REFUSED'}:
                break
    except Exception:
        # Keep progress/pre-state; do not publish secrets or an invented success.
        results.append({'step_id': 'job_failure', 'worker_result': build_result(worker_id='bounded_job',
            operation='job.execute', status='FAILED', errors=[{'code': 'JOB_EXECUTION_FAILED'}],
            continuation='STOP_FAILED', reason_code='JOB_EXECUTION_FAILED')})
    complete = len(results) == len(plan['steps']) and all(row['worker_result']['status'] == 'COMPLETE' for row in results)
    packet = build_result(worker_id='bounded_job', operation='job.execute', status='COMPLETE' if complete else 'PARTIAL',
        result={'schema': 'truecore.bounded_job_receipt@1', 'job_id': plan['job_id'],
            'plan_sha256': binding['plan_sha256'], 'original_request_sha256': plan['original_request_sha256'],
            'execution_status': 'completed' if complete else 'partial',
            'verification_scope': 'EXACT_WORKER_RESULTS_AND_REFERENCED_ARTIFACT_HASHES',
            'elapsed_seconds': round(time.monotonic() - start, 6), 'steps': results,
            'unexecuted_steps': [step['step_id'] for step in plan['steps']
                                if step['step_id'] not in {r['step_id'] for r in results if r.get('execution') == 'worker_invoked'}]},
        continuation='STOP_COMPLETE' if complete else 'STOP_PARTIAL',
        reason_code='ALL_STEPS_COMPLETE' if complete else 'JOB_HAS_UNRESOLVED_OR_FAILED_STEPS')
    atomic(terminal, canonical(packet))
    progress.unlink()
    return inspect_receipt(terminal, binding['plan_sha256'])


def inspect_receipt(path, expected_plan_sha256):
    packet = json.loads(regular(Path(path)))
    validate_result(packet)
    if packet['worker_id'] != 'bounded_job' or packet['result']['plan_sha256'] != expected_plan_sha256:
        raise ValueError('JOB_RECEIPT_IDENTITY_MISMATCH')
    for step in packet['result']['steps']:
        native = step['worker_result']
        validate_result(native)
        for artifact in native['artifacts']:
            if sha(regular(artifact['path'])) != artifact['sha256']:
                raise ValueError('JOB_ARTIFACT_CHANGED')
    return packet


class JobBoundary:
    """The caller selects one admitted job ID; no paths, grants or commands."""
    def __init__(self, jobs=None):
        self.jobs = json.loads(json.dumps(jobs or {}))

    def invoke(self, arguments):
        correction = None
        if not isinstance(arguments, dict):
            correction = 'INVALID_ARGUMENTS'
        elif set(arguments) & {'root', 'output_root', 'plan_path', 'plan_sha256', 'approval_sha256', 'commands', 'grants', 'budget'}:
            correction = 'FORBIDDEN_ARGUMENTS'
        elif set(arguments) - set(JOB_ARGUMENTS):
            correction = 'UNKNOWN_ARGUMENTS'
        elif 'job_id' not in arguments:
            correction = 'REQUIREMENTS_MISSING'
        elif not isinstance(arguments['job_id'], str) or not re.fullmatch(JOB_ARGUMENTS['job_id']['pattern'], arguments['job_id']):
            correction = 'INVALID_ARGUMENTS'
        if correction:
            return build_result(worker_id='bounded_job', operation='job.execute', status='REFUSED',
                result={'schema': 'truecore.operation_requirements@1', 'status': correction,
                        'required': JOB_ARGUMENTS,
                        'optional': {}, 'retryable': True}, continuation='RETRY_WITH_CORRECTED_BINDING',
                reason_code=correction)
        binding = self.jobs.get(arguments['job_id'])
        if binding is None:
            return build_result(worker_id='bounded_job', operation='job.execute', status='REFUSED',
                continuation='STOP_REFUSED', reason_code='UNAUTHORIZED_JOB')
        plan, _ = load_plan(binding)
        if plan['job_id'] != arguments['job_id']:
            raise ValueError('JOB_BINDING_IDENTITY_MISMATCH')
        packet = execute_job(binding)
        # The full private receipt is inspected by the host/operator. The public
        # result does not duplicate source paths, test logs or recovery topology.
        native = packet.get('result') or {}
        return build_result(worker_id='bounded_job', operation='job.execute', status=packet['status'],
            result={'job_id': plan['job_id'], 'job_receipt_sha256': packet['result_sha256'],
                    'execution_status': native.get('execution_status', 'unresolved'),
                    'step_statuses': [{'step_id': row['step_id'], 'status': row['worker_result']['status'],
                                      'reason': row['worker_result']['continuation']['reason_code']}
                                     for row in native.get('steps', [])]},
            continuation=packet['continuation']['state'], reason_code=packet['continuation']['reason_code'])
