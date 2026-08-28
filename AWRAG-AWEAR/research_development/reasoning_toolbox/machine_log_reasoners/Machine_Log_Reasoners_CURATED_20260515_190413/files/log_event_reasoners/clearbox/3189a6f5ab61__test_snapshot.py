'''
Tests for the snapshot command group.
'''

import unittest
import shutil
import json
from pathlib import Path
import sys

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.runtime import ConfigLoader
from commands.snapshot import create_snapshot, list_snapshots

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class TestSnapshotCommand(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("test_snapshot_dir")
        shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir()
        (self.test_dir / "config").mkdir()
        (self.test_dir / "data" / "snapshots").mkdir(parents=True)
        (self.test_dir / "data" / "lexicon").mkdir(parents=True)

        # Create a dummy defaults.json, which ConfigLoader requires
        with open(self.test_dir / "config" / "defaults.json", "w") as f:
            json.dump({}, f)

        # Create a dummy config loader
        self.config_loader = ConfigLoader(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_create_and_list_snapshot(self):
        # 1. Create a snapshot
        reason = "Unit test snapshot"
        create_args = Args(config_loader=self.config_loader, reason=reason)
        create_snapshot(create_args)

        # Check that the snapshot directory was created
        snapshot_dirs = list((self.test_dir / "data" / "snapshots").iterdir())
        self.assertEqual(len(snapshot_dirs), 1)
        snapshot_dir = snapshot_dirs[0]
        self.assertTrue((snapshot_dir / "manifest.json").exists())

        # 2. List snapshots and check the output
        list_args = Args(config_loader=self.config_loader)
        
        # Redirect stdout to capture print output
        from io import StringIO
        captured_output = StringIO()
        sys.stdout = captured_output

        list_snapshots(list_args)

        sys.stdout = sys.__stdout__  # Reset stdout
        output = captured_output.getvalue()

        self.assertIn(reason, output)
        self.assertIn(snapshot_dir.name, output)

if __name__ == "__main__":
    unittest.main()

