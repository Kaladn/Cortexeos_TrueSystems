"""Extract exact source facts without importing or interpreting an agent."""
import ast
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def build_usage(source_path, manifest):
    raw = source_path.read_bytes()
    text = raw.decode("utf-8")
    scope = ast.parse(text).body
    symbol = manifest["source_entrypoint"].split(":", 1)[1]
    for part in symbol.split("."):
        matches = [n for n in scope if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == part]
        if len(matches) != 1:
            raise ValueError("ambiguous or absent definition: " + symbol)
        node = matches[0]
        scope = node.body
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError("entrypoint is not a function")
    if "sha256:" + hashlib.sha256(raw).hexdigest() != manifest["source_entrypoint_hash"]:
        raise ValueError("source changed during extraction")
    def span(item):
        return ast.get_source_segment(text, item) if item is not None else None
    return {
        "schema": "truecore.agent_usage@1", "agent_id": manifest["agent_id"],
        "qualification": "STATIC_CODE_FACTS_ONLY",
        "source_entrypoint": manifest["source_entrypoint"],
        "source_entrypoint_hash": manifest["source_entrypoint_hash"],
        "runtime_hash": manifest["entrypoint_hash"],
        "definition": {"line": node.lineno, "end_line": node.end_lineno, "source": span(node)},
        "parameters": {"positional_only": [span(a) for a in node.args.posonlyargs],
            "positional": [span(a) for a in node.args.args],
            "keyword_only": [span(a) for a in node.args.kwonlyargs],
            "vararg": span(node.args.vararg), "kwarg": span(node.args.kwarg),
            "trailing_positional_default_expressions": [span(d) for d in node.args.defaults],
            "keyword_default_expressions": [span(d) for d in node.args.kw_defaults]},
        "return_annotation": span(node.returns),
        "unresolved": ["purpose", "prerequisites", "dependencies", "effects", "permissions",
                       "result_semantics", "failure_conditions", "retry", "examples", "backend_qualification"]}


def validate_usage(manifest):
    usage = manifest.get("usage")
    if not isinstance(usage, dict) or usage.get("schema") != "truecore.agent_usage@1":
        raise ValueError("missing or invalid agent usage contract")
    if manifest.get("usage_sha256") != digest(usage):
        raise ValueError("agent usage hash mismatch")
    for key in ("agent_id", "source_entrypoint", "source_entrypoint_hash"):
        if usage.get(key) != manifest.get(key):
            raise ValueError("agent usage binding mismatch: " + key)
    if usage.get("runtime_hash") != manifest.get("entrypoint_hash"):
        raise ValueError("agent usage runtime mismatch")
    if usage.get("qualification") != "STATIC_CODE_FACTS_ONLY":
        raise ValueError("unsupported help qualification")
    path = manifest.get("usage_source_path")
    if not isinstance(path, str) or not Path(path).is_file():
        raise ValueError("help source unavailable")
    if build_usage(Path(path), manifest) != usage:
        raise ValueError("help differs from current source")


def help_entry(manifest):
    validate_usage(manifest)
    usage = manifest["usage"]
    return {"label": manifest["agent_id"], "category": "Code-derived agent help",
        "tier1": {"what": usage["source_entrypoint"], "when": usage["qualification"]},
        "tier2": {"concept": json.dumps(usage["parameters"], sort_keys=True),
                  "misunderstanding": "Static source is not observed execution or authorization."},
        "tier3": {"how": usage["definition"]["source"], "failure_modes": "Unresolved: " + ", ".join(usage["unresolved"])},
        "usage": usage, "usage_sha256": manifest["usage_sha256"]}


def load_entries(agent_dir):
    entries = {}
    for path in sorted(Path(agent_dir).glob("*.agent.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        key = "agent:" + str(manifest.get("agent_id", path.stem))
        if key in entries:
            raise ValueError("duplicate agent help identity: " + key)
        if "usage" not in manifest:
            entries[key] = {"label": key, "category": "Agent usage unresolved",
                "tier1": {"what": "Code-derived usage missing.", "when": "UNRESOLVED"}}
        else:
            entries[key] = help_entry(manifest)
    return entries
