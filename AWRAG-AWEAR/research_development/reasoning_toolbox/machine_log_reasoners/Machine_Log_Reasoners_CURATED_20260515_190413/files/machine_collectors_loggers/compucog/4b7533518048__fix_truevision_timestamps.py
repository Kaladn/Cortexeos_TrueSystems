#!/usr/bin/env python3
"""
Automated Fix Script for truevision_event_live.py Timestamp Violations

Replaces all `time.time()` calls with `self.chronos.now()` for 
CONTRACT_ATLAS.md compliance.

Usage:
    python fix_truevision_timestamps.py [path_to_file]
    
Example:
    python fix_truevision_timestamps.py gaming/truevision_event_live.py
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime


def fix_timestamp_violations(filepath: Path) -> tuple[bool, int]:
    """
    Replace all time.time() with self.chronos.now() in file.
    
    Args:
        filepath: Path to truevision_event_live.py
    
    Returns:
        (success, num_changes) tuple
    """
    print(f"\n{'='*70}")
    print(f"TrueVision Timestamp Fix — CONTRACT_ATLAS.md Compliance")
    print(f"{'='*70}\n")
    
    # Validation
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False, 0
    
    if filepath.name != "truevision_event_live.py":
        print(f"⚠️  Warning: Expected 'truevision_event_live.py', got '{filepath.name}'")
        proceed = input("Continue anyway? [y/N]: ")
        if proceed.lower() != 'y':
            return False, 0
    
    print(f"📄 Target file: {filepath}")
    
    # Read original content
    print(f"📖 Reading file...")
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Count violations before fix
    violations_before = original_content.count('time.time()')
    print(f"🔍 Found {violations_before} timestamp violations")
    
    if violations_before == 0:
        print(f"✅ File already compliant! No changes needed.")
        return True, 0
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.with_suffix(f'.py.bak.{timestamp}')
    print(f"📦 Creating backup: {backup_path.name}")
    shutil.copy2(filepath, backup_path)
    
    # Apply fix
    print(f"🔧 Applying fix...")
    fixed_content = original_content.replace('time.time()', 'self.chronos.now()')
    
    # Verify fix
    violations_after = fixed_content.count('time.time()')
    chronos_calls = fixed_content.count('self.chronos.now()')
    
    if violations_after > 0:
        print(f"⚠️  Warning: {violations_after} violations remain after fix!")
        return False, 0
    
    # Write fixed content
    print(f"💾 Writing fixed file...")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ FIX APPLIED SUCCESSFULLY")
    print(f"{'='*70}\n")
    print(f"Changes made:")
    print(f"  • Replaced {violations_before} × time.time() → self.chronos.now()")
    print(f"  • Total chronos.now() calls: {chronos_calls}")
    print(f"  • Remaining violations: {violations_after}")
    print(f"\nBackup saved:")
    print(f"  • {backup_path}")
    print(f"\nVerification commands:")
    print(f"  # Should return 0 matches:")
    print(f"  grep 'time\\.time()' {filepath}")
    print(f"\n  # Should return {violations_before} matches:")
    print(f"  grep 'self\\.chronos\\.now()' {filepath}")
    
    return True, violations_before


def main():
    """Main entry point."""
    print("\n")
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("❌ Missing required argument: file path")
        print("\nUsage:")
        print("  python fix_truevision_timestamps.py <path_to_truevision_event_live.py>")
        print("\nExample:")
        print("  python fix_truevision_timestamps.py gaming/truevision_event_live.py")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    # Apply fix
    success, num_changes = fix_timestamp_violations(filepath)
    
    if success:
        if num_changes > 0:
            print(f"\n🎉 SUCCESS! File is now CONTRACT_ATLAS.md compliant.")
            print(f"\nNext steps:")
            print(f"  1. Review changes: diff {filepath} {filepath}.bak.*")
            print(f"  2. Run tests: cd event_system && python test_full_pipeline.py")
            print(f"  3. Validate: cd gaming && python truevision_event_live.py --duration 30")
        sys.exit(0)
    else:
        print(f"\n❌ Fix failed. Original file unchanged.")
        print(f"   Review errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
