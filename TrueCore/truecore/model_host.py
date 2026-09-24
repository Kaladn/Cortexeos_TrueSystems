"""JSONL model-output transport to TrueCore only; does not load/train an LLM.

Host configuration is supplied out-of-band, never in a model turn. No HTTP,
shell, model-specified imports, legacy control API dispatch or alternate tools.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
from .operator_boundary import OperatorBoundary, canonical, digest, strict_json

class ModelHost:
    def __init__(self, boundary, *, max_calls=64, max_request_bytes=65536, caller_identity=None):
        if type(max_calls) is not int or not 1 <= max_calls <= 10000:
            raise ValueError('INVALID_CALL_BUDGET')
        if type(max_request_bytes) is not int or not 1 <= max_request_bytes <= 1_000_000:
            raise ValueError('INVALID_REQUEST_BUDGET')
        self._boundary = boundary
        self._max_calls = max_calls
        self._max_request_bytes = max_request_bytes
        self._calls = 0
        self._seen = {}
        self._caller_identity = caller_identity

    def accept(self, raw):
        def bind_caller(packet):
            if self._caller_identity is not None:
                packet['caller_identity'] = self._caller_identity
                packet['receipt_sha256'] = digest({k: v for k, v in packet.items() if k != 'receipt_sha256'})
            return packet

        def reject(reason):
            packet = {'schema': 'truecore.operator_result@1', 'status': 'REJECTED',
                      'reason': reason, 'result': None, 'continuation': 'STOP_UNRESOLVED',
                      'request_sha256': hashlib.sha256(raw).hexdigest(),
                      'verification_scope': 'TRANSPORT_REJECTION_NO_EXECUTION',
                      'execution_scope': 'NONE'}
            packet['receipt_sha256'] = digest(packet)
            return bind_caller(packet)
        if self._calls >= self._max_calls:
            return reject('CALL_BUDGET_EXCEEDED')
        self._calls += 1
        if len(raw) > self._max_request_bytes:
            return reject('REQUEST_BUDGET_EXCEEDED')
        try:
            request = strict_json(raw)
            canonical_request = canonical(request)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return reject('INVALID_JSON')
        request_id = request.get('request_id') if isinstance(request, dict) else None
        if isinstance(request_id, str) and request_id in self._seen:
            old, result = self._seen[request_id]
            if old != canonical_request:
                return reject('REQUEST_ID_REUSE_MISMATCH')
            return strict_json(result)
        result = bind_caller(self._boundary.handle(request))
        # Every result is cached for stable request identity. Corrected bindings use
        # a NEW request ID; immutable host bindings cannot be changed by a turn.
        if isinstance(request_id, str):
            self._seen[request_id] = (canonical_request, canonical(result))
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-config', required=True)
    args = parser.parse_args()
    descriptor = os.open(args.host_config, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as f:
        info = os.fstat(f.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                info.st_mode & (stat.S_IRWXG | stat.S_IRWXO) or os.getuid() != os.geteuid()):
            raise ValueError('HOST_CONFIG_NOT_PRIVATE_OR_WRONG_OWNER')
        config = strict_json(f.read(4_000_001))
    base_fields = {'schema', 'grants', 'artifacts', 'max_calls', 'max_request_bytes'}
    optional_fields = {'worker_grants', 'resources', 'machine_worker_grants', 'machine_resources', 'jobs'}
    if not isinstance(config, dict) or not base_fields <= set(config) or not set(config) <= base_fields | optional_fields:
        raise ValueError('INVALID_HOST_CONFIG')
    if config['schema'] != 'truecore.model_host@1':
        raise ValueError('INVALID_HOST_SCHEMA')
    caller_identity = {'kind': 'local_os_uid', 'uid': os.getuid()}
    host = ModelHost(OperatorBoundary(
                         grants=config['grants'],
                         artifacts=config['artifacts'],
                         worker_grants=config.get('worker_grants', []),
                         resources=config.get('resources', {}),
                         machine_worker_grants=config.get('machine_worker_grants', []),
                         machine_resources=config.get('machine_resources', {}),
                         jobs=config.get('jobs', {}),
                         caller_identity=caller_identity,
                     ),
                     max_calls=config['max_calls'], max_request_bytes=config['max_request_bytes'],
                     caller_identity=caller_identity)
    while True:
        line = sys.stdin.buffer.readline(host._max_request_bytes + 1)
        if not line:
            break
        response = host.accept(line)
        sys.stdout.buffer.write(canonical(response) + b'\n')
        sys.stdout.buffer.flush()
        if response.get('reason') in ('REQUEST_BUDGET_EXCEEDED', 'CALL_BUDGET_EXCEEDED'):
            break

if __name__ == '__main__':
    main()
