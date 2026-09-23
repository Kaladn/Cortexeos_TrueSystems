from __future__ import annotations

import argparse
import json
from pathlib import Path

from .memory import (
    add_file,
    ask,
    attach_source,
    build_sqlite_support,
    import_demo,
    index_source,
    init_runtime,
    inspect_binary,
    list_sources,
)
from .relational_v2 import ingest_native_chat, project_relationships, retrieve_v2


def main() -> None:
    parser = argparse.ArgumentParser(prog="local-memory-chat", description="Local Memory Chat demo CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create ignored local runtime folders")
    init_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    init_cmd.add_argument("--profile", default="default")

    import_demo_cmd = sub.add_parser("import-demo", help="Import synthetic demo chat into hot memory")
    import_demo_cmd.add_argument("--demo", type=Path, default=Path("data/demo/synthetic_chat.jsonl"))
    import_demo_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    import_demo_cmd.add_argument("--profile", default="default")

    add_file_cmd = sub.add_parser("add-file", help="Add one local file to hot memory with line citations")
    add_file_cmd.add_argument("path", type=Path)
    add_file_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    add_file_cmd.add_argument("--profile", default="default")
    add_file_cmd.add_argument("--label")
    add_file_cmd.add_argument("--chunk-lines", type=int, default=12)

    attach_cmd = sub.add_parser("attach-source", help="Attach a private source read-only without indexing it")
    attach_cmd.add_argument("--path", type=Path, required=True)
    attach_cmd.add_argument("--source-type", choices=["chat-binary", "file-root", "file"], required=True)
    attach_cmd.add_argument("--label", required=True)
    attach_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    attach_cmd.add_argument("--profile", default="default")

    sources_cmd = sub.add_parser("sources", help="List attached private/runtime sources")
    sources_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    sources_cmd.add_argument("--profile", default="default")

    index_cmd = sub.add_parser("index-source", help="Index one attached source into hot memory")
    index_cmd.add_argument("--source-id", required=True)
    index_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    index_cmd.add_argument("--profile", default="default")
    index_cmd.add_argument("--hot", action="store_true", help="Required for v0; indexes into hot memory")
    index_cmd.add_argument("--chunk-lines", type=int, default=12)

    inspect_cmd = sub.add_parser("inspect-binary", help="Inspect an attached chat-binary source without decoding it")
    inspect_cmd.add_argument("--source-id", required=True)
    inspect_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    inspect_cmd.add_argument("--profile", default="default")
    inspect_cmd.add_argument("--sample-bytes", type=int, default=64)

    sqlite_cmd = sub.add_parser("sqlite-support", help="Convert an attached SQLite source into a runtime support binary")
    sqlite_cmd.add_argument("--source-id", required=True)
    sqlite_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    sqlite_cmd.add_argument("--profile", default="default")
    sqlite_cmd.add_argument("--table", action="append", dest="tables", help="SQLite table to convert; repeatable")
    sqlite_cmd.add_argument("--limit-per-table", type=int, help="Optional safety limit for each table")
    sqlite_cmd.add_argument("--allow-live-source", action="store_true", help="Allow conversion if the attached SQLite hash changed; receipt records the mismatch")

    ask_cmd = sub.add_parser("ask", help="Search hot memory and write a cited memory packet")
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--runtime-root", type=Path, default=Path("runtime"))
    ask_cmd.add_argument("--profile", default="default")
    ask_cmd.add_argument("--limit", type=int, default=5)
    ask_cmd.add_argument("--json", action="store_true", help="Print full JSON result")

    native_cmd = sub.add_parser("native-chat-intake", help="Admit one native historical chat immutably")
    native_cmd.add_argument("path", type=Path)
    native_cmd.add_argument("--source-type", choices=["codex", "openai-export", "lm-studio"], required=True)
    native_cmd.add_argument("--conversation-id", help="Required for a multi-conversation OpenAI export")
    native_cmd.add_argument("--runtime-root", type=Path, required=True)

    project_cmd = sub.add_parser("relational-v2-project", help="Project an ephemeral relationship field from selected blocks or sentences")
    project_cmd.add_argument("center_surface")
    project_cmd.add_argument("--scope", action="append", required=True, help="Immutable block or sentence ID; repeatable")
    project_cmd.add_argument("--offset", action="append", type=int, dest="offsets", help="Signed non-zero offset; repeatable; default is 6-1-6")
    project_cmd.add_argument("--top-k", type=int)
    project_cmd.add_argument("--include-positional-mass", action="store_true")
    project_cmd.add_argument("--runtime-root", type=Path, required=True)

    v2_ask_cmd = sub.add_parser("relational-v2-ask", help="Retrieve a bounded relational v2 packet")
    v2_ask_cmd.add_argument("question")
    v2_ask_cmd.add_argument("--runtime-root", type=Path, required=True)
    v2_ask_cmd.add_argument("--limit", type=int, default=6)
    v2_ask_cmd.add_argument("--max-chars", type=int, default=24000)

    args = parser.parse_args()
    if args.command == "init":
        result = init_runtime(args.runtime_root, memory_profile_id=args.profile)
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "import-demo":
        result = import_demo(args.demo, runtime_root=args.runtime_root, memory_profile_id=args.profile)
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "add-file":
        result = add_file(
            args.path,
            runtime_root=args.runtime_root,
            memory_profile_id=args.profile,
            source_label=args.label,
            chunk_lines=args.chunk_lines,
        )
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "attach-source":
        result = attach_source(
            args.path,
            source_type=args.source_type,
            label=args.label,
            runtime_root=args.runtime_root,
            memory_profile_id=args.profile,
        )
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "sources":
        result = list_sources(args.runtime_root, memory_profile_id=args.profile)
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "index-source":
        result = index_source(
            args.source_id,
            runtime_root=args.runtime_root,
            memory_profile_id=args.profile,
            hot=args.hot,
            chunk_lines=args.chunk_lines,
        )
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "inspect-binary":
        result = inspect_binary(
            args.source_id,
            runtime_root=args.runtime_root,
            memory_profile_id=args.profile,
            sample_bytes=args.sample_bytes,
        )
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "sqlite-support":
        result = build_sqlite_support(
            args.source_id,
            runtime_root=args.runtime_root,
            memory_profile_id=args.profile,
            tables=args.tables,
            limit_per_table=args.limit_per_table,
            allow_live_source=args.allow_live_source,
        )
        print(json.dumps(result, ensure_ascii=True))
    elif args.command == "ask":
        result = ask(args.question, runtime_root=args.runtime_root, memory_profile_id=args.profile, limit=args.limit)
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(format_ask_result(result))
    elif args.command == "native-chat-intake":
        print(json.dumps(ingest_native_chat(
            args.path,
            source_type=args.source_type,
            conversation_id=args.conversation_id,
            runtime_root=args.runtime_root,
        ), ensure_ascii=True))
    elif args.command == "relational-v2-project":
        print(json.dumps(project_relationships(
            args.center_surface,
            runtime_root=args.runtime_root,
            scope_ids=args.scope,
            offsets=args.offsets,
            top_k=args.top_k,
            include_positional_mass=args.include_positional_mass,
        ), ensure_ascii=True))
    elif args.command == "relational-v2-ask":
        print(json.dumps(retrieve_v2(args.question, runtime_root=args.runtime_root, limit=args.limit, max_chars=args.max_chars), ensure_ascii=True))
    else:
        parser.error("unknown command")


def format_ask_result(result: dict[str, object]) -> str:
    packet = result.get("packet") if isinstance(result.get("packet"), dict) else {}
    evidence = packet.get("evidence_items") if isinstance(packet.get("evidence_items"), list) else []
    lines = [
        "Local Memory Chat",
        f"question: {packet.get('question')}",
        "",
        "Found memory:",
    ]
    if not evidence:
        lines.append("- none")
    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- [{index}] {item.get('citation')} score={item.get('score')} "
            f"source={item.get('source_label')} time={item.get('timestamp')}"
        )
        lines.append(f"  {item.get('snippet')}")
    lines.extend(
        [
            "",
            f"packet: {result.get('packet_path')}",
            f"receipt: {(result.get('receipt') or {}).get('receipt_path') if isinstance(result.get('receipt'), dict) else None}",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
