'''
Snapshot command group for creating, listing, and rolling back system snapshots.
'''

import logging
import json
import shutil
from datetime import datetime
from pathlib import Path

def create_snapshot(args):
    logger = logging.getLogger("snapshot_cmd")
    snapshots_path = args.config_loader.base_path / "data" / "snapshots"
    snapshots_path.mkdir(exist_ok=True)

    # Create a timestamped directory for the snapshot
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_utc")
    snapshot_dir = snapshots_path / timestamp
    snapshot_dir.mkdir()

    logger.info(f"Creating new snapshot in: {snapshot_dir}")

    # Copy config file
    config_path = args.config_loader.user_config_path
    if config_path.exists():
        shutil.copy(config_path, snapshot_dir)

    # Copy lexicon data (placeholder)
    lexicon_path = args.config_loader.base_path / "data" / "lexicon"
    if lexicon_path.exists():
        shutil.copytree(lexicon_path, snapshot_dir / "lexicon")

    # Write manifest
    manifest = {
        "timestamp": timestamp,
        "reason": args.reason,
        "config_file": str(config_path.name),
        "lexicon_included": lexicon_path.exists()
    }
    with open(snapshot_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully created snapshot: {timestamp}")

def list_snapshots(args):
    logger = logging.getLogger("snapshot_cmd")
    snapshots_path = args.config_loader.base_path / "data" / "snapshots"
    
    if not snapshots_path.exists() or not any(snapshots_path.iterdir()):
        print("No snapshots found.")
        return

    print(f"{'TIMESTAMP':<25} {'REASON'}")
    for snapshot_dir in sorted(snapshots_path.iterdir(), reverse=True):
        if snapshot_dir.is_dir() and (snapshot_dir / "manifest.json").exists():
            with open(snapshot_dir / "manifest.json", "r") as f:
                manifest = json.load(f)
                print(f"{manifest['timestamp']:<25} {manifest.get('reason', 'N/A')}")

def register(subparsers, config_loader, plugin_manager):
    '''Registers the snapshot command group.'''
    parser = subparsers.add_parser("snapshot", help="Create, list, and rollback system snapshots.")
    snapshot_subparsers = parser.add_subparsers(dest="action", help="Snapshot actions")

    # Create command
    create_parser = snapshot_subparsers.add_parser("create", help="Create a new system snapshot.")
    create_parser.add_argument("reason", nargs="?", default="Manual snapshot", help="A brief reason for creating the snapshot.")
    create_parser.set_defaults(func=create_snapshot, config_loader=config_loader)

    # List command
    list_parser = snapshot_subparsers.add_parser("list", help="List all available snapshots.")
    list_parser.set_defaults(func=list_snapshots, config_loader=config_loader)

