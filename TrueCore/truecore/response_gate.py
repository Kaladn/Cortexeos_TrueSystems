"""Host-reviewed publication gate. No automatic semantic safety claim.

Approvals are out-of-band host configuration, never fields in model output.
Bind exact conversation/turn/context and text; no partial streaming release.
This application boundary does not sandbox a malicious host process.
"""
from .operator_boundary import digest

def proposal_key(proposal):
    if not isinstance(proposal,dict) or set(proposal)!={'conversation_id','turn_id','context_sha256','text'}:
        raise ValueError('INVALID_RESPONSE_FIELDS')
    if not all(isinstance(v,str) and v for v in proposal.values()):
        raise ValueError('INVALID_RESPONSE_VALUES')
    if len(proposal['context_sha256'])!=64 or any(c not in '0123456789abcdef' for c in proposal['context_sha256']):
        raise ValueError('INVALID_CONTEXT_HASH')
    if len(proposal['text'].encode())>65536:raise ValueError('RESPONSE_TOO_LARGE')
    return digest(proposal)

class ResponseGate:
    def __init__(self, *, approved_keys=()):
        self._approved=frozenset(approved_keys)

    def publish(self, proposal):
        try:key=proposal_key(proposal)
        except (ValueError,TypeError):
            return {'status':'REJECTED','text':None,'reason':'INVALID_RESPONSE_PROPOSAL'}
        allowed=key in self._approved
        result={'schema':'truecore.response_publication@1',
                'status':'HOST_REVIEW_APPROVED' if allowed else 'HELD_FOR_HOST_REVIEW',
                'proposal_sha256':key,'text':proposal['text'] if allowed else None,
                'verification_scope':'EXACT_HOST_APPROVAL_NOT_AUTOMATIC_SAFETY_OR_FACT_CHECK',
                'tool_execution':False}
        result['receipt_sha256']=digest(result)
        return result

def main():
    """Host-side reviewed publication; not exposed as a model command."""
    import argparse
    import json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal',type=Path,required=True)
    parser.add_argument('--host-approvals',type=Path,required=True)
    args=parser.parse_args()
    from .operator_boundary import strict_json
    approvals=strict_json(args.host_approvals.read_bytes())
    if not isinstance(approvals,list) or not all(isinstance(x,str) and len(x)==64 for x in approvals):
        raise ValueError('INVALID_HOST_APPROVALS')
    print(json.dumps(ResponseGate(approved_keys=approvals).publish(strict_json(args.proposal.read_bytes()))))

if __name__=='__main__':main()
