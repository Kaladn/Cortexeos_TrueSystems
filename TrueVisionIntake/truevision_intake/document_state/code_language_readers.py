"""Exact lexical reading and verified grammar adapters for derived code text."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Error
from pygments.util import ClassNotFound


LEXER_NAMES = {
    "python": "python", "py": "python",
    "javascript": "javascript", "javascript_jsx": "jsx",
    "typescript": "typescript", "typescript_tsx": "tsx",
    "powershell": "powershell", "windows_batch": "batch", "windows_command": "batch",
    "c": "c", "cpp": "cpp", "c_cpp_header": "cpp", "cpp_header": "cpp",
    "csharp": "csharp", "rust": "rust", "shell": "bash", "bash": "bash",
    "zsh": "bash", "fish": "fish", "java": "java", "kotlin": "kotlin",
    "kotlin_script": "kotlin", "go": "go", "ruby": "ruby", "lua": "lua",
    "php": "php", "swift": "swift", "sql": "sql", "fsharp": "fsharp",
}


def _lexical_read(text: str, language: str) -> dict[str, Any]:
    lexer_name = LEXER_NAMES.get(language)
    if lexer_name is None:
        return {"status": "NOT_IMPLEMENTED", "language": language, "exact_text_reconstructed": False, "tokens": []}
    try:
        lexer = get_lexer_by_name(lexer_name, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return {"status": "NOT_IMPLEMENTED_MISSING_LEXER", "language": language, "lexer": lexer_name, "tokens": []}
    rows = []
    cursor = 0
    reconstructed = []
    for token_type, surface in lex(text, lexer):
        value = str(surface)
        rows.append({
            "kind": str(token_type),
            "exact": value,
            "character_start": cursor,
            "character_end_exclusive": cursor + len(value),
            "error": token_type in Error,
        })
        reconstructed.append(value)
        cursor += len(value)
    exact = "".join(reconstructed) == text
    if not exact:
        raise RuntimeError("language lexer changed exact derived code text")
    return {
        "status": "exact_lexical_read",
        "language": language,
        "lexer": f"pygments:{lexer_name}",
        "tokens": rows,
        "token_count": len(rows),
        "error_token_count": sum(1 for row in rows if row["error"]),
        "exact_text_reconstructed": True,
        "grammar_verified": False,
    }


def _javascript_syntax(text: str) -> dict[str, Any]:
    executable = shutil.which("node")
    if executable is None:
        return {"status": "NOT_IMPLEMENTED_MISSING_PARSER", "parser": "node_v8_check", "execution_performed": False}
    try:
        result = subprocess.run(
            [executable, "--check", "-"],
            input=text,
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            env={"PATH": "/usr/bin:/bin", "NODE_OPTIONS": ""},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "parser_unavailable", "parser": "node_v8_check", "error_type": type(error).__name__, "execution_performed": False}
    return {
        "status": "syntax_verified" if result.returncode == 0 else "syntax_rejected",
        "parser": "node_v8_check",
        "return_code": result.returncode,
        "execution_performed": False,
        "behavior_proven": False,
    }


def read_code_language_structure(text: str, declared_language: str) -> dict[str, Any]:
    """Return exact lexical structure plus a real parser result where supported."""

    language = declared_language.strip().casefold()
    lexical = _lexical_read(text, language)
    if language == "javascript":
        grammar = _javascript_syntax(text)
    else:
        grammar = {
            "status": "handled_by_primary_python_adapter" if language in {"python", "py"} else "NOT_IMPLEMENTED",
            "execution_performed": False,
        }
    return {
        "schema": "truevision_code_language_structure@1",
        "declared_language": declared_language,
        "language_inferred": False,
        "lexical": lexical,
        "grammar": grammar,
        "execution_import_eval_and_compile_performed": False,
    }
