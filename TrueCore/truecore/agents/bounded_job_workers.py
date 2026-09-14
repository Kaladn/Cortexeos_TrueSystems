"""Registered workers for exact admitted edits, external checks and readiness.

The operator writes code; these deterministic workers never invent a patch,
test, source, historical link, causal attribution, or success result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from truecore.bounded_jobs import (atomic, bounded_process, canonical, check_hashes,
    environment, load_plan, regular, sha)
from truecore.live_agents.worker_result import build_result


def selected(binding, step_id, worker_id):
    plan, directory = load_plan(binding)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('JOB_NOT_STARTED')
    progress = json.loads(regular(directory / 'progress.json'))
    if progress['plan_sha256'] != binding['plan_sha256'] or progress['pending_step'] != step_id:
        raise ValueError('STEP_NOT_DISPATCHED')
    step = next(s for s in plan['steps'] if s['step_id'] == step_id)
    if step['worker_id'] != worker_id:
        raise ValueError('WRONG_WORKER')
    return step['config'], directory


def patch_files(binding: dict, step_id: str) -> dict:
    worker = 'job_patch_files'
    config, directory = selected(binding, step_id, worker)
    if set(config) != {'root', 'files'} or not isinstance(config['files'], list) or not 1 <= len(config['files']) <= 16:
        raise ValueError('INVALID_PATCH_PLAN')
    root = Path(config['root'])
    if not root.is_absolute() or not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('INVALID_PATCH_ROOT')
    targets, seen, total = [], set(), 0
    for row in config['files']:
        if set(row) != {'path', 'before_sha256', 'content_utf8'}:
            raise ValueError('INVALID_PATCH_FILE')
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('PATCH_ROOT_ESCAPE')
        path = root / relative
        if path in seen or any(p.is_symlink() for p in (path, *path.parents)) or not path.parent.is_dir():
            raise ValueError('UNSAFE_PATCH_TARGET')
        seen.add(path)
        before = regular(path) if path.exists() else None
        if (sha(before) if before is not None else None) != row['before_sha256']:
            raise ValueError('PATCH_PRECONDITION_FAILED')
        after = row['content_utf8'].encode('utf-8')
        total += len(after) + len(before or b'')
        if total > 4_000_000:
            raise ValueError('PATCH_BYTE_BUDGET')
        mode = path.stat().st_mode & 0o777 if before is not None else 0o644
        if mode & 0o022:
            raise ValueError('SHARED_WRITABLE_PATCH_TARGET')
        targets.append((path, before, after, mode))
    # Preserve every pre-state before touching any target. Missing originals
    # remain explicitly absent; no fabricated empty-file backup.
    backup = directory / 'prestate'
    backup.mkdir(mode=0o700, exist_ok=True)
    artifacts, transitions = [], []
    for path, before, after, mode in targets:
        if before is not None:
            saved = backup / sha(before)
            if saved.exists():
                if regular(saved) != before:
                    raise ValueError('PRESTATE_CHANGED')
            else:
                atomic(saved, before)
            artifacts.append({'kind': 'preserved_prestate', 'path': str(saved), 'sha256': sha(before)})
    status, reason = 'COMPLETE', 'EXACT_PATCH_BYTES_VERIFIED'
    try:
        for path, before, after, mode in targets:
            observed = regular(path) if path.exists() else None
            if observed != before or any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('PATCH_TARGET_DRIFT')
            atomic(path, after, mode)
            if regular(path) != after:
                raise ValueError('PATCH_POSTCONDITION_FAILED')
            transitions.append({'relative_path': str(path.relative_to(root)),
                'before_sha256': sha(before) if before is not None else None, 'after_sha256': sha(after)})
            artifacts.append({'kind': 'verified_patched_source', 'path': str(path), 'sha256': sha(after)})
    except Exception:
        status, reason = 'FAILED', 'PATCH_PARTIAL_FAILURE_PRESTATE_PRESERVED'
    return build_result(worker_id=worker, operation='source.patch', status=status,
        result={'applied_files': transitions, 'verification_scope': 'EXACT_FILE_BYTES_NOT_BEHAVIOR',
                'recovery': 'PRESTATE_PRESERVED_NO_AUTOMATIC_OVERWRITE'}, artifacts=artifacts,
        errors=[] if status == 'COMPLETE' else [{'code': reason}],
        continuation='STOP_COMPLETE' if status == 'COMPLETE' else 'STOP_FAILED', reason_code=reason)


def acceptance_run(binding: dict, step_id: str) -> dict:
    worker = 'job_acceptance_run'
    config, directory = selected(binding, step_id, worker)
    if set(config) != {'script', 'script_sha256', 'source_bindings', 'timeout_seconds', 'max_output_bytes'}:
        raise ValueError('INVALID_ACCEPTANCE_BINDING')
    script = Path(config['script'])
    if script.suffix != '.py' or sha(regular(script)) != config['script_sha256']:
        raise ValueError('ACCEPTANCE_SCRIPT_CHANGED')
    check_hashes(config['source_bindings'])
    env = environment()
    fixture_root = directory / (step_id + '-fixtures')
    fixture_root.mkdir(mode=0o700)
    env['TMPDIR'] = str(fixture_root)
    code, raw, reason, elapsed = bounded_process([sys.executable, '-B', str(script)],
        cwd=fixture_root, timeout=config['timeout_seconds'], maximum=config['max_output_bytes'], env=env)
    log = directory / (step_id + '.log')
    atomic(log, raw)
    check_hashes(config['source_bindings'])
    check_hashes([{'path': str(script), 'sha256': config['script_sha256']}])
    status = 'COMPLETE' if code == 0 and reason is None else 'FAILED'
    return build_result(worker_id=worker, operation='acceptance.run', status=status,
        result={'process_returncode': code, 'elapsed_seconds': elapsed,
            'script_sha256': config['script_sha256'],
            'verification_scope': 'EXACT_ADMITTED_TEST_SCRIPT_EXIT_AND_OUTPUT_NOT_UNEXERCISED_BEHAVIOR'},
        artifacts=[{'kind': 'acceptance_output', 'path': str(log), 'sha256': sha(raw)}],
        errors=[] if status == 'COMPLETE' else [{'code': reason or 'ACCEPTANCE_FAILED'}],
        continuation='STOP_COMPLETE' if status == 'COMPLETE' else 'STOP_FAILED',
        reason_code='ACCEPTANCE_PROCESS_PASSED' if status == 'COMPLETE' else (reason or 'ACCEPTANCE_FAILED'))


def history_readiness(binding: dict, step_id: str) -> dict:
    """Report evidence requirements; never pretend readiness is history analysis."""
    worker = 'job_history_readiness'
    config, _ = selected(binding, step_id, worker)
    if set(config) != {'source_bindings'} or not isinstance(config['source_bindings'], list):
        raise ValueError('INVALID_HISTORY_BINDING')
    if config['source_bindings']:
        check_hashes(config['source_bindings'])
    requirements = [
        {'need': 'instruction_ownership', 'required_evidence': 'original speaker, exact source span, quotation ownership and explicit interpretation links'},
        {'need': 'implementation_outcomes', 'required_evidence': 'source-linked operations and independently checked outcomes'},
        {'need': 'capability_lineage', 'required_evidence': 'versioned implementations and explicit or qualified continuity links; names alone insufficient'},
        {'need': 'supersession', 'required_evidence': 'explicit supersedes decision; silence remains unresolved'},
        {'need': 'relationship_decay', 'required_evidence': 'comparable covered time windows and a frozen descriptive metric'},
        {'need': 'causal_attribution', 'required_evidence': 'qualified causal identification beyond temporal association'},
    ]
    return build_result(worker_id=worker, operation='history.readiness', status='UNRESOLVED',
        result={'history_analysis_executed': False, 'bound_source_count': len(config['source_bindings']),
                'actor_blame_inferred': False, 'ready_for_causal_claims': False},
        unresolved=requirements + [{'code': 'HISTORICAL_SOURCE_NOT_BOUND' if not config['source_bindings'] else 'HISTORICAL_SCHEMA_AND_LINKS_NOT_QUALIFIED'}],
        continuation='STOP_NO_EVIDENCE', reason_code='HISTORY_EVIDENCE_PREREQUISITES_REQUIRED')


def history_order(binding: dict, step_id: str) -> dict:
    """Delegate exact admitted block ordering to its TrueMem owner."""
    worker = 'job_history_order'
    config, directory = selected(binding, step_id, worker)
    if set(config) != {'blocks_path', 'blocks_sha256', 'dataset_id'}:
        raise ValueError('INVALID_HISTORY_ORDER_BINDING')
    raw = regular(config['blocks_path'])
    if sha(raw) != config['blocks_sha256']:
        raise ValueError('HISTORY_SOURCE_CHANGED')
    blocks = [json.loads(line) for line in raw.splitlines() if line]
    from truemem.engine.history_projection import project_history_order
    projection = project_history_order(config['dataset_id'], blocks)
    if sha(regular(config['blocks_path'])) != config['blocks_sha256']:
        raise ValueError('HISTORY_SOURCE_CHANGED')
    path = directory / (step_id + '.projection.json')
    atomic(path, canonical(projection))
    return build_result(worker_id=worker, operation='history.order', status='PARTIAL',
        result={'node_count': len(projection['nodes']), 'relationship_count': len(projection['relationships']),
                'source_sha256': config['blocks_sha256'], 'claim_class': projection['claim_class']},
        unresolved=[{'code': 'NOT_IMPLEMENTED', 'need': need} for need in projection['unsupported']],
        artifacts=[{'kind': 'speaker_preserving_order_projection', 'path': str(path), 'sha256': sha(regular(path))}],
        continuation='STOP_PARTIAL', reason_code='ORDER_IS_NOT_CAUSAL_OR_INSTRUCTION_OWNERSHIP_PROOF')


def graph_review(binding: dict, step_id: str) -> dict:
    """Rerun all fifteen registered graph workers; preserve missing authority."""
    worker = 'job_graph_review'
    config, directory = selected(binding, step_id, worker)
    if set(config) != {'map_dir', 'manifest_sha256', 'scopes', 'limit', 'source_root'}:
        raise ValueError('INVALID_GRAPH_JOB_BINDING')
    from truecore.registered_worker_bridge import RegisteredWorkerBridge, RESOURCE_KIND
    import csv
    from truecore.bounded_jobs import AGENTS
    with (AGENTS / 'catalog/repository_graph_worker_source.csv').open() as stream:
        ids = [row['operator_id'] for row in csv.DictReader(stream)]
    resource = {'kind': RESOURCE_KIND, 'path': config['map_dir'],
                'manifest_sha256': config['manifest_sha256'], 'allowed_scopes': config['scopes']}
    bridge = RegisteredWorkerBridge(worker_grants=ids, resources={'review-map': resource})
    packets = [bridge.invoke({'worker_id': worker_id, 'resource_id': 'review-map',
        'parameters': {'limit': config['limit'], 'scopes': config['scopes']}}) for worker_id in ids]
    map_dir = Path(config['map_dir'])
    # Exact source comparison prevents historical edges being advertised as the
    # post-edit worktree. No absent edge is promoted into safety or dead-code proof.
    manifest = json.loads(regular(map_dir / 'manifest.json'))
    files_entry = manifest['artifacts']['files']
    raw = regular(map_dir / files_entry['path'])
    if sha(raw) != files_entry['sha256']:
        raise ValueError('GRAPH_FILES_ARTIFACT_CHANGED')
    changed, missing = [], []
    for row in (json.loads(line) for line in raw.splitlines() if line):
        path = Path(config['source_root']) / row['path']
        if not path.is_file():
            missing.append(row['path'])
        else:
            # File hashes include large immutable research sources; stream them.
            import hashlib
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1048576), b''):
                    digest.update(chunk)
            if digest.hexdigest() != row['sha256']:
                changed.append(row['path'])
    payload = {'schema': 'truecore.graph_review_bundle@1', 'snapshot_id': manifest['snapshot_id'],
               'map_use': 'HISTORICAL_SNAPSHOT', 'current_source_mismatches': changed,
               'missing_mapped_sources': missing, 'new_unmapped_source_discovery': 'NOT_PERFORMED',
               'worker_packets': packets}
    path = directory / (step_id + '.graph.json')
    atomic(path, canonical(payload))
    unavailable = [p['worker_id'] for p in packets if p['status'] == 'NOT_IMPLEMENTED']
    return build_result(worker_id=worker, operation='graph.review', status='PARTIAL',
        result={'workers_executed': len(packets), 'unsupported_workers': unavailable,
                'map_use': 'HISTORICAL_SNAPSHOT', 'changed_mapped_sources': len(changed)},
        unresolved=[{'code': 'HISTORICAL_MAP_NOT_CURRENT_WORKTREE'}] +
                   [{'code': 'NOT_IMPLEMENTED', 'worker_id': name} for name in unavailable],
        artifacts=[{'kind': 'canonical_graph_review_bundle', 'path': str(path), 'sha256': sha(regular(path))}],
        continuation='STOP_PARTIAL', reason_code='STATIC_GRAPH_WITH_EXPLICIT_AUTHORITY_GAPS')
