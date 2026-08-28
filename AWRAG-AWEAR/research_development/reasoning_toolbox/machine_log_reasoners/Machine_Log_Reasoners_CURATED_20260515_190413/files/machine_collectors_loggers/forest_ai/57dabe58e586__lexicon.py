'''
Lexicon command group for managing the system's vocabulary.
'''

import logging
import json
from pathlib import Path

def add_to_lexicon(args):
    logger = logging.getLogger("lexicon_cmd")
    lexicon_path = args.config_loader.base_path / "data" / "lexicon"
    lexicon_path.mkdir(exist_ok=True)
    lexicon_file = lexicon_path / "master_lexicon.json"

    if not lexicon_file.exists():
        lexicon = {}
    else:
        with open(lexicon_file, "r") as f:
            lexicon = json.load(f)

    term = args.term.lower()
    if term not in lexicon:
        lexicon[term] = {
            "added": datetime.utcnow().isoformat(),
            "frequency": 1,
            "symbol": args.symbol # Placeholder
        }
        logger.info(f"Added new term '{term}' to the lexicon.")
    else:
        lexicon[term]["frequency"] += 1
        logger.info(f"Updated frequency for term '{term}'.")

    with open(lexicon_file, "w") as f:
        json.dump(lexicon, f, indent=2)

    print(f"Successfully processed term: {term}")

def lexicon_status(args):
    logger = logging.getLogger("lexicon_cmd")
    lexicon_path = args.config_loader.base_path / "data" / "lexicon"
    lexicon_file = lexicon_path / "master_lexicon.json"

    if not lexicon_file.exists():
        print("Lexicon is empty.")
        return

    with open(lexicon_file, "r") as f:
        lexicon = json.load(f)

    print(f"Lexicon Status:")
    print(f"  Total Terms: {len(lexicon)}")
    # Add more stats in the future


from datetime import datetime

def register(subparsers, config_loader, plugin_manager):
    '''Registers the lexicon command group.'''
    parser = subparsers.add_parser("lexicon", help="Manage the system's vocabulary.")
    lexicon_subparsers = parser.add_subparsers(dest="action", help="Lexicon actions")

    # Add command
    add_parser = lexicon_subparsers.add_parser("add", help="Add or update a term in the lexicon.")
    add_parser.add_argument("term", help="The term to add.")
    add_parser.add_argument("--symbol", default=None, help="An optional symbol to associate with the term.")
    add_parser.set_defaults(func=add_to_lexicon, config_loader=config_loader)

    # Status command
    status_parser = lexicon_subparsers.add_parser("status", help="Display the status of the lexicon.")
    status_parser.set_defaults(func=lexicon_status, config_loader=config_loader)

