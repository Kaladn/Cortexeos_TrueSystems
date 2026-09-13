"""Narrow model-facing TrueCore boundary. No app startup or live capture.

Host code supplies grants and immutable artifact bindings; model requests cannot
change them. This is an application boundary, not an OS sandbox.
"""
from __future__ import annotations
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from .operator_contracts import contracts
from .registered_worker_bridge import RegisteredWorkerBridge, RegisteredWorkerBridgeError

OPERATIONS = MappingProxyType({
    'help.list': 'List this boundary and its limits; does not execute a component.',
    'sensory.inspect': 'Inspect one host-admitted TrueMachine Fusion Pack, preserving source ownership.',
    'help.query': 'Read the code-grounded help map; guidance is not execution proof.',
    'source.classify': 'Classify a host-admitted text source using existing DocuFilm rules; does not admit it.',
    'media.describe': 'Describe an admitted media tool declaration; does not execute or qualify the media tool.',
    'worker.invoke': 'Invoke one host-granted registered read-only worker on one host-bound resource.',
})

def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY')
            value[key] = item
        return value
    def constant(value):
        raise ValueError('NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

class Rejected(ValueError):
    pass

class OperatorBoundary:
    def __init__(self, *, grants, artifacts, worker_grants=(), resources=None, max_bytes=4_000_000):
        if not set(grants) <= OPERATIONS.keys():
            raise ValueError('UNKNOWN_HOST_GRANT')
        self.grants = frozenset(grants)
        self.artifacts = MappingProxyType({k: MappingProxyType(dict(v)) for k, v in artifacts.items()})
        self.worker_bridge = RegisteredWorkerBridge(worker_grants=worker_grants, resources=resources)
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError('INVALID_HOST_BUDGET')
        self.max_bytes = max_bytes

    def handle(self, request):
        # The canonical request hash also rejects non-JSON/NaN input.
        request_hash = digest(request)
        result, status, reason = None, 'REJECTED', None
        try:
            if not isinstance(request, dict) or set(request) != {'schema', 'request_id', 'operation', 'arguments'}:
                raise Rejected('INVALID_REQUEST_FIELDS')
            if request['schema'] != 'truecore.operator_request@1':
                raise Rejected('UNSUPPORTED_SCHEMA')
            if not isinstance(request['request_id'], str) or not request['request_id']:
                raise Rejected('INVALID_REQUEST_ID')
            operation = request['operation']
            if not isinstance(operation, str) or operation not in OPERATIONS:
                raise Rejected('NOT_IMPLEMENTED_AT_MODEL_BOUNDARY')
            if operation not in self.grants:
                raise Rejected('PERMISSION_DENIED')
            args = request['arguments']
            if not isinstance(args, dict):
                raise Rejected('INVALID_ARGUMENTS')
            if operation == 'help.list':
                if args:
                    raise Rejected('INVALID_ARGUMENTS')
                result = {'operations': dict(OPERATIONS), 'source': 'TrueCore',
                          'contracts': contracts(),
                          'registered_workers': self.worker_bridge.public_contract(),
                          'live_capture': False, 'mutation': False,
                          'limits': ['Only listed operations are connected.',
                                     'Host grants are not human approval for other operations.']}
                status = 'COMPLETE'
            elif operation == 'sensory.inspect':
                result = self._inspect(args)
                status = 'PARTIAL' if any(o['status'] == 'error' for o in result['observations']) else 'COMPLETE'
            elif operation == 'worker.invoke':
                result = self.worker_bridge.invoke(args)
                status = 'COMPLETE' if result['status'] == 'COMPLETE' else 'PARTIAL'
            else:
                from .operator_workers import dispatch_read_worker
                result = dispatch_read_worker(operation, args, self._read_artifact)
                status = 'COMPLETE'
        except (Rejected, RegisteredWorkerBridgeError) as e:
            reason = str(e)
        except (OSError, UnicodeError, json.JSONDecodeError):
            status, reason = 'FAILED', 'ARTIFACT_READ_FAILED'
        except (ValueError, TypeError, KeyError, RecursionError):
            status, reason = 'REJECTED', 'INVALID_WORKER_INPUT'
        packet = {'schema': 'truecore.operator_result@1', 'request_sha256': request_hash,
                  'status': status, 'reason': reason, 'result': result,
                  'continuation': ('STOP_COMPLETE' if status == 'COMPLETE' else
                                   'STOP_PARTIAL' if status == 'PARTIAL' else 'STOP_UNRESOLVED'),
                  'verification_scope': 'STRUCTURE_AND_HOST_BOUND_HASHES_NOT_SEMANTIC_TRUTH',
                  'execution_scope': 'READ_ONLY_ADMITTED_ARTIFACT_NO_CAPTURE_OR_ACTION'}
        packet['receipt_sha256'] = digest(packet)
        return packet

    def _read_artifact(self, artifact_id):
        if not isinstance(artifact_id, str) or not artifact_id:
            raise Rejected('INVALID_ARGUMENT_BINDING')
        binding = self.artifacts.get(artifact_id)
        if binding is None:
            raise Rejected('MISSING_PREREQUISITE')
        # Only the host can bind a filesystem path. No model path, command or import.
        path = Path(binding['path'])
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                raise Rejected('REGULAR_ARTIFACT_REQUIRED')
            raw = f.read(self.max_bytes + 1)
        if len(raw) > self.max_bytes:
            raise Rejected('ARTIFACT_BUDGET_EXCEEDED')
        if hashlib.sha256(raw).hexdigest() != binding['sha256']:
            raise Rejected('STALE_OR_CHANGED_ARTIFACT')
        return raw, path.name, binding['sha256']

    def _inspect(self, args):
        if set(args) != {'artifact_id', 'expected_run_id', 'expected_sequence'}:
            raise Rejected('INVALID_ARGUMENTS')
        if not all(isinstance(args[k], str) and args[k] for k in ('artifact_id', 'expected_run_id')):
            raise Rejected('INVALID_ARGUMENT_BINDING')
        if type(args['expected_sequence']) is not int or args['expected_sequence'] < 1:
            raise Rejected('INVALID_ARGUMENT_BINDING')
        raw, _, _ = self._read_artifact(args['artifact_id'])
        pack = strict_json(raw)
        fields = {'schema', 'run_id', 'sequence', 'cadence_ns', 'timeline_ns', 'time', 'observations'}
        if not isinstance(pack, dict) or set(pack) != fields or pack['schema'] != 'truemachine.fusion@1':
            raise Rejected('INVALID_FUSION_SCHEMA')
        if pack['run_id'] != args['expected_run_id'] or pack['sequence'] != args['expected_sequence']:
            raise Rejected('WRONG_RUN_OR_SEQUENCE')
        if (type(pack['sequence']) is not int or pack['sequence'] < 1 or
            type(pack['cadence_ns']) is not int or pack['cadence_ns'] <= 0 or
            type(pack['timeline_ns']) is not int or
            pack['timeline_ns'] != (pack['sequence'] - 1) * pack['cadence_ns']):
            raise Rejected('INVALID_TIMELINE')
        if not isinstance(pack['time'], dict) or not isinstance(pack['observations'], list) or not pack['observations']:
            raise Rejected('INVALID_OBSERVATIONS')
        t = pack['time']
        if set(t) != {'utc', 'utc_date', 'unix_time_ns', 'monotonic_ns', 'elapsed_ns', 'clock_offset_ns', 'boot_id'}:
            raise Rejected('INVALID_TIME_SCHEMA')
        if not all(type(t[k]) is int for k in ('unix_time_ns', 'monotonic_ns', 'elapsed_ns', 'clock_offset_ns')):
            raise Rejected('INVALID_TIME_TYPES')
        seconds, nanos = divmod(t['unix_time_ns'], 1_000_000_000)
        try:
            utc = datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + f'.{nanos:09d}Z'
        except (ValueError, OverflowError, OSError):
            raise Rejected('INVALID_TIME_RANGE')
        if t['utc'] != utc or t['utc_date'] != utc[:10] or not isinstance(t['boot_id'], str) or not t['boot_id']:
            raise Rejected('INCONSISTENT_TIME')
        for o in pack['observations']:
            if not isinstance(o, dict) or set(o) != {'source', 'schema', 'status', 'data', 'source_coordinates', 'content_sha256', 'error'}:
                raise Rejected('INVALID_OBSERVATION')
            if not all(isinstance(o[k], str) and o[k] for k in ('source', 'schema')):
                raise Rejected('INVALID_OBSERVATION_IDENTITY')
            if (not isinstance(o['data'], dict) or not isinstance(o['source_coordinates'], list) or
                not o['source_coordinates'] or not all(isinstance(x, str) and x for x in o['source_coordinates'])):
                raise Rejected('INVALID_OBSERVATION_COORDINATES')
            if o['status'] not in ('ok', 'error'):
                raise Rejected('INVALID_OBSERVATION_STATUS')
            if o['status'] == 'error' and (o['data'] or not isinstance(o['error'], str) or not o['error']):
                raise Rejected('INVALID_ERROR_OBSERVATION')
            if o['status'] == 'ok' and o['error'] is not None:
                raise Rejected('INVALID_OK_OBSERVATION')
            # TrueMachine uses ensure_ascii=True, not this boundary's canonical format.
            encoded = json.dumps(o['data'], ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            if hashlib.sha256(encoded).hexdigest() != o['content_sha256']:
                raise Rejected('OBSERVATION_HASH_MISMATCH')
        return pack
