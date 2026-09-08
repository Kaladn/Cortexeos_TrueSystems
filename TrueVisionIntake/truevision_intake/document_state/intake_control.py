"""Durable, single-writer DocuFilm pause/child/return accounting.

Hashes witness integrity and identity, never recognition correctness.
No tools, model calls, or source mutations are performed by this controller.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def context(state):
    node = state['stack'][-1] if state['stack'] else {}
    return dict(object_id=node.get('id'), parent_id=node.get('parent_id'),
                source_hash=node.get('source_hash'), position=node.get('cursor'),
                state_hash=digest(state))


def transition(state, kind, data, seq):
    """Pure reducer used both before publication and during journal replay."""
    stack = state['stack']
    if kind == 'START':
        if stack or state.get('started'):
            raise ValueError('already started')
        if not data['source_hash'] or not data['object_id']:
            raise ValueError('source identity required')
        state['started'] = True
        stack.append(dict(id=data['object_id'], source_hash=data['source_hash'], cursor=0, phase='RUNNING'))
        return
    if not stack:
        raise ValueError('no active object')
    node = stack[-1]
    phase = node['phase']
    if kind == 'DETECTION_STARTED' and phase == 'RUNNING':
        if data['position'] != node['cursor']:
            raise ValueError('position does not match cursor')
        node.update(phase='DETECTING', detection_start=seq)
    elif kind == 'DETECTION_ENDED' and phase == 'DETECTING':
        children = data['children']
        ids = [c['id'] for c in children]
        if len(ids) != len(set(ids)) or any(not c['id'] or not c['source_hash'] for c in children):
            raise ValueError('duplicate or missing child identity')
        if set(ids) & {n['id'] for n in stack}:
            raise ValueError('cyclic object identity')
        if data['start_mark'] != node['detection_start']:
            raise ValueError('wrong detection start')
        node.update(phase='DETECTED', children=copy.deepcopy(children), outcomes={}, detection_end=seq)
    elif kind == 'PARENT_PAUSED' and phase == 'DETECTED':
        if data['next_position'] != node['cursor'] + 1:
            raise ValueError('resume would skip or repeat a position')
        node.update(phase='PAUSED', pause_mark=seq, saved_hash=digest(node), next_position=data['next_position'])
    elif kind == 'CHILD_RETRY' and phase == 'PAUSED':
        outcome = node['outcomes'].get(data['child_id'])
        if not outcome or outcome['status'] != 'FAILED' or not data.get('reason'):
            raise ValueError('retry requires a failed child and explicit reason')
        del node['outcomes'][data['child_id']]
    elif kind == 'CHILD_STARTED' and phase == 'PAUSED':
        child = next((c for c in node['children'] if c['id'] == data['child_id']), None)
        if child is None or data['child_id'] in node['outcomes']:
            raise ValueError('unknown or already accounted child')
        stack.append(dict(id=child['id'], source_hash=child['source_hash'], cursor=0,
                          phase='RUNNING', start_mark=seq, parent_id=node['id']))
    elif kind == 'CHILD_ENDED' and len(stack) > 1 and phase == 'RUNNING':
        if data['start_mark'] != node['start_mark']:
            raise ValueError('wrong child start')
        if data['status'] not in {'COMPLETED', 'FAILED', 'CANCELLED', 'UNRESOLVED'}:
            raise ValueError('invalid terminal status')
        if not isinstance(data['result'], dict) or not data['result']:
            raise ValueError('terminal evidence or failure detail required')
        stack.pop()
        stack[-1]['outcomes'][node['id']] = dict(status=data['status'], result=data['result'], start_mark=node['start_mark'], end_mark=seq)
    elif kind == 'RETURN_TO_PARENT_PAUSE' and phase == 'PAUSED':
        if set(node['outcomes']) != {c['id'] for c in node['children']}:
            raise ValueError('unaccounted children')
        if data['pause_mark'] != node['pause_mark'] or data['saved_hash'] != node['saved_hash']:
            raise ValueError('wrong pause or saved state')
        if state['policy'] == 'require_success' and any(o['status'] != 'COMPLETED' for o in node['outcomes'].values()):
            raise ValueError('child failure blocks resume')
        node['phase'] = 'RETURNED'
    elif kind == 'PARENT_RESUMED' and phase == 'RETURNED':
        node['cursor'] = node['next_position']
        node['phase'] = 'RUNNING'
    elif kind == 'FINISH' and len(stack) == 1 and phase == 'RUNNING':
        if data['positions'] != node['cursor']:
            raise ValueError('incomplete source positions')
        stack.pop()
        state['finished'] = True
    else:
        raise ValueError(f'illegal transition: {phase} -> {kind}')


class IntakeControl:
    """Atomic checkpoint journal. One owner per path; reopen only after it exits."""
    def __init__(self, path, *, run_id, policy='require_success'):
        if policy not in {'require_success', 'account_all'}:
            raise ValueError('unknown failure policy')
        self.path = Path(path)
        self.header = dict(schema='docufilm_intake_control@1', run_id=run_id, policy=policy)
        self.events = []
        self.state = dict(stack=[], policy=policy)
        if self.path.exists():
            stored = json.loads(self.path.read_text())
            if stored['header'] != self.header:
                raise ValueError('journal binding mismatch')
            previous = digest(self.header)
            for seq, event in enumerate(stored['events'], 1):
                body = {k: v for k, v in event.items() if k != 'hash'}
                if event['seq'] != seq or event['previous'] != previous or digest(body) != event['hash']:
                    raise ValueError('journal integrity failure')
                if event['context'] != context(self.state):
                    raise ValueError('journal custody mismatch')
                transition(self.state, event['kind'], event['data'], seq)
                previous = event['hash']
            self.events = stored['events']

    def mark(self, kind, **data):
        state = copy.deepcopy(self.state)
        seq = len(self.events) + 1
        transition(state, kind, data, seq)
        event = dict(seq=seq, kind=kind, data=data, context=context(self.state),
                     previous=self.events[-1]['hash'] if self.events else digest(self.header))
        event['hash'] = digest(event)
        events = self.events + [event]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.pending')
        with temporary.open('x') as stream:
            json.dump(dict(header=self.header, events=events), stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.state, self.events = state, events
        return seq


def intake_state_movie(manifest_path, journal_path, *, run_id, reader, max_positions=None):
    """Read stored frames, detect glyph objects, intake each, and resume exactly.

    max_positions bounds this invocation, not the source. Reopening verifies the
    manifest and every stored cell chunk before continuing. An interrupted child
    is re-read deterministically; this adapter has no mutating child effects.
    """
    from .document_state_movie import extract_black_glyph_patterns_from_state_movie
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    chunks = manifest['cell_state']['chunks']
    for chunk in chunks:
        path = Path(chunk['path'])
        if not path.is_absolute():
            path = manifest_path.parent / path
        actual = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != chunk['sha256']:
            raise ValueError('cell chunk integrity failure')
    source_hash = digest(manifest)
    reader_hash = digest(dict(lexicon={k: asdict(v) for k, v in reader._lexicon._by_hash.items()},
                              counts=reader._lifetime_counts._by_glyph_id, threshold=128.0))
    if max_positions is not None and (type(max_positions) is not int or max_positions < 0):
        raise ValueError('max_positions must be a nonnegative integer')
    control = IntakeControl(journal_path, run_id=run_id)
    if not control.events:
        control.mark('START', object_id=manifest['source_id'], source_hash=source_hash, reader_hash=reader_hash)
    if control.events[0]['data']['source_hash'] != source_hash or control.events[0]['data']['reader_hash'] != reader_hash:
        raise ValueError('source revision changed')
    count = int(manifest['records']['frame_count'])
    if count < 1 or sum(int(c['frames']) for c in chunks) != count:
        raise ValueError('inconsistent frame inventory')
    processed = 0
    while not control.state.get('finished'):
        root = control.state['stack'][0]
        frame = root['cursor']
        if root['phase'] == 'RUNNING' and (frame == count or (max_positions is not None and processed >= max_positions)):
            if frame == count:
                control.mark('FINISH', positions=count)
            break
        node = control.state['stack'][-1]
        if len(control.state['stack']) > 1:
            item = next(c for c in root['children'] if c['id'] == node['id'])
            try:
                result = reader.read_page_frame(source_id=root['id'], frame_id=str(frame), page_number=frame+1,
                                               glyph_cells=[dict(rows=item['pattern'], bbox=item['bbox'])])
            except Exception as error:
                control.mark('CHILD_ENDED', start_mark=node['start_mark'], status='FAILED',
                             result=dict(error_type=type(error).__name__, message=str(error)))
                break
            control.mark('CHILD_ENDED', start_mark=node['start_mark'], status='COMPLETED', result=result)
        elif node['phase'] == 'RUNNING':
            control.mark('DETECTION_STARTED', position=frame)
        elif node['phase'] == 'DETECTING':
            patterns = extract_black_glyph_patterns_from_state_movie(manifest_path=manifest_path, frame_index=frame)
            children = [dict(id=digest([source_hash, frame, p['order'], p]), source_hash=digest(p), **p) for p in patterns]
            control.mark('DETECTION_ENDED', start_mark=node['detection_start'], children=children)
        elif node['phase'] == 'DETECTED':
            control.mark('PARENT_PAUSED', next_position=frame+1)
        elif node['phase'] == 'PAUSED':
            if any(o['status'] != 'COMPLETED' for o in node['outcomes'].values()):
                break
            pending = [c for c in node['children'] if c['id'] not in node['outcomes']]
            if pending:
                control.mark('CHILD_STARTED', child_id=pending[0]['id'])
            else:
                control.mark('RETURN_TO_PARENT_PAUSE', pause_mark=node['pause_mark'], saved_hash=node['saved_hash'])
        elif node['phase'] == 'RETURNED':
            control.mark('PARENT_RESUMED')
            processed += 1
    blocked = any(o['status'] != 'COMPLETED' for n in control.state['stack'] for o in n.get('outcomes', {}).values())
    return dict(status='COMPLETE' if control.state.get('finished') else ('BLOCKED' if blocked else 'PAUSED'),
                finished=bool(control.state.get('finished')), positions=count if control.state.get('finished') else control.state['stack'][0]['cursor'],
                marks=len(control.events), journal=str(control.path), journal_hash=control.events[-1]['hash'])
