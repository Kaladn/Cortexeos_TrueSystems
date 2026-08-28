"""Generate structural tier: permanent canonical entries for digits, letters, punctuation.

Output:
  Lexical Data/Structural/structural.json — ~95 entries, pre-assigned STRUCTURAL status

Address range: 0x000000000001 — 0x0000000000FF (reserved, well below all pools)
These never change, never get returned, never go through the approval pipeline.
"""
import json
import os

LEXICAL_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "Lexical Data")
STRUCTURAL_DIR = os.path.join(LEXICAL_ROOT, "Structural")
STRUCTURAL_START = 0x000000000001


def make_structural_entry(addr: int, char: str, display: str, category: str) -> dict:
    hex_str = f"0x{addr:012X}"
    return {
        "binary": f"{addr:048b}",
        "hex": hex_str,
        "symbol": hex_str,
        "word": char,
        "display": display,
        "category": category,
        "font_symbol": f"STRUCT_{display}",
        "tone_signature": f"TONE_STRUCT_{addr}",
        "status": "STRUCTURAL",
        "pack": "structural",
    }


def main():
    entries = []
    addr = STRUCTURAL_START

    # ── Digits 0-9 ──
    for d in "0123456789":
        entries.append(make_structural_entry(addr, d, f"DIGIT_{d}", "digit"))
        addr += 1

    # ── Lowercase letters a-z ──
    for c in "abcdefghijklmnopqrstuvwxyz":
        entries.append(make_structural_entry(addr, c, f"LETTER_{c}", "letter_lower"))
        addr += 1

    # ── Uppercase letters A-Z ──
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        entries.append(make_structural_entry(addr, c, f"LETTER_{c}", "letter_upper"))
        addr += 1

    # ── Punctuation & keyboard symbols ──
    punct_map = [
        ("!", "EXCLAMATION"),
        ("@", "AT"),
        ("#", "HASH"),
        ("$", "DOLLAR"),
        ("%", "PERCENT"),
        ("^", "CARET"),
        ("&", "AMPERSAND"),
        ("*", "ASTERISK"),
        ("(", "LPAREN"),
        (")", "RPAREN"),
        ("-", "HYPHEN"),
        ("_", "UNDERSCORE"),
        ("=", "EQUALS"),
        ("+", "PLUS"),
        ("[", "LBRACKET"),
        ("]", "RBRACKET"),
        ("{", "LBRACE"),
        ("}", "RBRACE"),
        ("|", "PIPE"),
        ("\\", "BACKSLASH"),
        (";", "SEMICOLON"),
        (":", "COLON"),
        ("'", "APOSTROPHE"),
        ('"', "DOUBLE_QUOTE"),
        (",", "COMMA"),
        (".", "PERIOD"),
        ("/", "SLASH"),
        ("<", "LESS_THAN"),
        (">", "GREATER_THAN"),
        ("?", "QUESTION"),
        ("~", "TILDE"),
        ("`", "BACKTICK"),
    ]
    for char, name in punct_map:
        entries.append(make_structural_entry(addr, char, f"PUNCT_{name}", "punctuation"))
        addr += 1

    # ── Write ──
    os.makedirs(STRUCTURAL_DIR, exist_ok=True)
    out_path = os.path.join(STRUCTURAL_DIR, "structural.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=2)

    print(f"Structural tier: {len(entries)} entries")
    print(f"Address range: 0x{STRUCTURAL_START:012X} — 0x{addr - 1:012X}")
    print(f"Wrote: {out_path}")

    # Summary
    cats = {}
    for e in entries:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    for cat, count in cats.items():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
