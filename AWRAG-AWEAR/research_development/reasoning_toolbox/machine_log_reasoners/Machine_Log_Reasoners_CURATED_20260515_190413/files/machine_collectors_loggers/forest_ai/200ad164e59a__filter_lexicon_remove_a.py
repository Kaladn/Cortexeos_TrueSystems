"""Create a filtered lexicon with all entries not starting with 'a'."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator, Dict, Any

SOURCE = Path("Lexicon_Canonical/lexicon_v2.json")
DEST = Path("Lexicon_Canonical/lexicon_v2_without_a.json")


def iter_json_array(path: Path) -> Iterator[Dict[str, Any]]:
    decoder = json.JSONDecoder()
    buffer = ""
    with path.open("r", encoding="utf-8") as handle:
        in_array = False
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            buffer += chunk
            while True:
                if not in_array:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break
                    if buffer[0] != "[":
                        raise ValueError(f"Expected '[' at start of {path}")
                    buffer = buffer[1:]
                    in_array = True

                buffer = buffer.lstrip()
                if not buffer:
                    break
                if buffer[0] == "]":
                    return
                try:
                    obj, idx = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                if isinstance(obj, dict):
                    yield obj
                buffer = buffer[idx:]
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:]
                    continue
                if buffer.startswith("]"):
                    return
        buffer = buffer.strip()
        if buffer and buffer != "]":
            raise ValueError(f"Unexpected trailing data while reading {path}")


def keep_entry(entry: dict) -> bool:
    word = entry.get("word") or entry.get("token")
    if not isinstance(word, str):
        return True
    return not word.lower().startswith("a")


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source lexicon missing: {SOURCE}")
    DEST.parent.mkdir(parents=True, exist_ok=True)

    kept = 0
    removed = 0
    last_report = time.time()

    with DEST.open("w", encoding="utf-8") as handle:
        handle.write("[\n")
        first = True
        for entry in iter_json_array(SOURCE):
            if keep_entry(entry):
                if not first:
                    handle.write(",\n")
                json.dump(entry, handle, ensure_ascii=False)
                first = False
                kept += 1
            else:
                removed += 1

            if kept % 100000 == 0 and kept > 0:
                now = time.time()
                if now - last_report >= 5:
                    print(f"processed={kept + removed:,} kept={kept:,} removed={removed:,}")
                    handle.flush()
                    last_report = now
        handle.write("\n]\n")

    print({"kept": kept, "removed": removed, "destination": str(DEST)})


if __name__ == "__main__":
    main()
