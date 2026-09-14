"""Read-only speaker-preserving order projection of admitted TrueMem blocks.

NEXT_TURN is order, never instruction ownership, interpretation, causation,
capability continuity, supersession, or a personality classification.
"""
from __future__ import annotations

from .native_publication import _temporal_graph


def project_history_order(dataset_id: str, blocks: list[dict]) -> dict:
    if not isinstance(dataset_id, str) or not dataset_id or not isinstance(blocks, list) or len(blocks) > 100000:
        raise ValueError('INVALID_HISTORY_BLOCKS')
    seen = set()
    ordinals = set()
    speakers = {}
    rejected = []
    admitted = []
    for block in blocks:
        if not isinstance(block, dict) or not {'block_id', 'block_ordinal'} <= set(block):
            raise ValueError('INVALID_HISTORY_BLOCK')
        if not isinstance(block['block_id'], str) or type(block['block_ordinal']) is not int or block['block_ordinal'] < 0:
            raise ValueError('INVALID_HISTORY_BLOCK_IDENTITY')
        if block['block_id'] in seen or block['block_ordinal'] in ordinals:
            raise ValueError('DUPLICATE_BLOCK_IDENTITY')
        seen.add(block['block_id'])
        ordinals.add(block['block_ordinal'])
        if block.get('dataset_id', dataset_id) != dataset_id:
            raise ValueError('FORBIDDEN_DATASET_JOIN')
        metadata = block.get('chat_metadata')
        if not isinstance(metadata, dict) or type(metadata.get('turn_index')) is not int or metadata.get('turn_index', -1) < 0 or not isinstance(metadata.get('conversation_id'), str) or not metadata.get('conversation_id'):
            rejected.append({'block_id': block['block_id'], 'reason': 'MISSING_EXPLICIT_TURN_IDENTITY'})
            continue
        identity = (metadata['conversation_id'], metadata['turn_index'], metadata.get('message_id'))
        speaker = metadata.get('speaker')
        if metadata.get('message_id') is not None and not isinstance(metadata['message_id'], str):
            raise ValueError('INVALID_MESSAGE_ID')
        if speaker is not None and not isinstance(speaker, str):
            raise ValueError('INVALID_SPEAKER')
        speakers.setdefault(identity, set()).add(speaker)
        admitted.append(block)
    ambiguous = {identity for identity, roles in speakers.items() if len(roles) != 1 or None in roles or '' in roles}
    filtered = []
    for block in admitted:
        metadata = block['chat_metadata']
        identity = (metadata['conversation_id'], metadata['turn_index'], metadata.get('message_id'))
        if identity in ambiguous:
            rejected.append({'block_id': block['block_id'], 'reason': 'AMBIGUOUS_SPEAKER'})
        else:
            filtered.append(block)
    nodes, edges, duplicates = _temporal_graph(dataset_id, filtered)
    for node in nodes:
        node['speaker_scope'] = 'MESSAGE_SPEAKER_NOT_AUTHOR_OF_ALL_QUOTED_CONTENT'
        node['instruction_owner'] = None
        node['causal_responsibility'] = None
    for edge in edges:
        edge['continuity'] = 'NEXT_RETAINED_UNAMBIGUOUS_TURN_NOT_PROOF_OF_COMPLETE_HISTORY'
    return {'schema': 'truemem.history_order_projection@1', 'dataset_id': dataset_id,
        'nodes': nodes, 'relationships': edges, 'rejected_blocks': rejected,
        'ambiguous_turn_count': duplicates, 'input_blocks': len(blocks),
        'claim_class': 'EXPLICIT_CONVERSATION_ORDER_ONLY',
        'unsupported': ['instruction_to_interpretation_links', 'operation_to_outcome_links',
            'capability_migration', 'supersession', 'relationship_decay', 'causal_attribution'],
        'source_mutation': False}
