"""Fixed read workers using existing component code. No dynamic runner names."""
import importlib
import sys
from pathlib import Path
from .operator_boundary import Rejected, strict_json

ROOT = Path(__file__).resolve().parents[2]

def _component(module, relative):
    root = (ROOT / relative).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    loaded = importlib.import_module(module)
    if not Path(loaded.__file__).resolve().is_relative_to(root):
        raise Rejected('COMPONENT_GENERATION_MISMATCH')
    return loaded

def dispatch_read_worker(operation, args, read_artifact):
    if operation == 'help.query':
        if set(args) != {'question', 'layer'} or not isinstance(args['question'], str) or not 0 < len(args['question']) <= 4096:
            raise Rejected('INVALID_ARGUMENTS')
        if type(args['layer']) is not int or args['layer'] not in (1, 2, 3):
            raise Rejected('INVALID_ARGUMENTS')
        if args['question'].startswith('agent:'):
            from .help.corpus import HelpCorpus
            entry = HelpCorpus().get(args['question'])
            if entry is None:
                raise Rejected('UNKNOWN_AGENT_HELP')
            return {'grade': 'GUIDANCE_NOT_EXECUTION_PROOF', 'help': entry}
        result = _component('truesystems_api.help', 'control-api/src').answer_help(args['question'], args['layer'])
        return {'grade': 'GUIDANCE_NOT_EXECUTION_PROOF', 'help': result}
    if set(args) != {'artifact_id'}:
        raise Rejected('INVALID_ARGUMENTS')
    raw, filename, sha = read_artifact(args['artifact_id'])
    if operation == 'source.classify':
        result = _component('truevision_intake.source_typing', 'TrueVisionIntake').classify_source(filename, raw.decode('utf-8'))
        return {'grade': 'SOURCE_CLASSIFICATION_NOT_ADMISSION', 'artifact_sha256': sha, 'classification': result}
    if operation == 'media.describe':
        tool = strict_json(raw)
        if not isinstance(tool, dict) or not isinstance(tool.get('tool_id'), str) or not tool['tool_id']:
            raise Rejected('INVALID_TOOL_DECLARATION')
        # Existing descriptor coerces bools; don't let 'false' become True.
        bool_fields = ('can_witness', 'can_profile', 'can_plan', 'can_replay', 'can_surface',
                       'observes_state', 'abstracts_behavior', 'generates_state', 'renders_media',
                       'copies_source_media', 'raw_video_saved', 'raw_media_saved', 'source_truth_compliant')
        if any(k in tool and type(tool[k]) is not bool for k in bool_fields):
            raise Rejected('INVALID_DECLARATION_BOOLEAN')
        result = _component('truevision_runtime.state_language', 'TrueVision').build_state_language(tool)
        return {'grade': 'DECLARATION_NOT_EXECUTION_PROOF', 'artifact_sha256': sha,
                'tool_id': tool['tool_id'], 'description': result, 'executable_from_model': False}
    raise Rejected('NOT_IMPLEMENTED_AT_MODEL_BOUNDARY')
