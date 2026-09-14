"""Model-visible contracts for the fixed read-only TrueCore worker surface."""
from copy import deepcopy

_CONTRACTS = {
    'help.list': {'arguments': {}, 'result_grade': 'BOUNDARY_OPERATION_CATALOG'},
    'help.query': {'arguments': {'question': 'nonempty string <=4096 characters', 'layer': 'integer 1|2|3'},
                   'result_grade': 'GUIDANCE_NOT_EXECUTION_PROOF'},
    'sensory.inspect': {'arguments': {'artifact_id': 'host-admitted nonempty string',
                                      'expected_run_id': 'witnessed nonempty string',
                                      'expected_sequence': 'witnessed integer >=1'},
                        'result_grade': 'STRUCTURE_AND_HASH_CHECKED_FUSION_NOT_SEMANTIC_TRUTH'},
    'source.classify': {'arguments': {'artifact_id': 'host-admitted UTF-8 source reference'},
                        'result_grade': 'SOURCE_CLASSIFICATION_NOT_ADMISSION'},
    'media.describe': {'arguments': {'artifact_id': 'host-admitted JSON tool declaration reference'},
                       'result_grade': 'DECLARATION_NOT_EXECUTION_PROOF'},
    'worker.invoke': {
        'arguments': {
            'worker_id': 'host-granted registered worker identity',
            'resource_id': 'host-bound resource identity',
            'parameters': {'limit': 'integer 1..100000'},
        },
        'result_grade': 'REGISTERED_WORKER_RESULT_NOT_OPERATOR_ANSWER',
    },
    'machine.invoke': {
        'arguments': {
            'worker_id': 'host-granted registered read-only TrueMachine worker identity',
            'resource_id': 'host-bound filesystem-root identity',
            'parameters': 'operation-specific typed parameters containing relative paths only',
        },
        'result_grade': 'OBSERVED_MACHINE_LOCATIONS_AND_MEASUREMENTS_NOT_SAFETY_JUDGMENT',
    },
}

def contracts():
    result = deepcopy(_CONTRACTS)
    for contract in result.values():
        contract.update({'extra_arguments': 'REJECT', 'effects': 'READ_ONLY',
                         'permission': 'EXPLICIT_HOST_GRANT_REQUIRED',
                         'retry': 'SAME_ID_SAME_REQUEST_REPLAYS; CORRECTION_REQUIRES_NEW_ID',
                         'bindings': ['REQUEST', 'WITNESSED_STATE', 'PREVIOUS_RESULT'],
                         'defaults': {}, 'model_may_authorize': False})
    return result
