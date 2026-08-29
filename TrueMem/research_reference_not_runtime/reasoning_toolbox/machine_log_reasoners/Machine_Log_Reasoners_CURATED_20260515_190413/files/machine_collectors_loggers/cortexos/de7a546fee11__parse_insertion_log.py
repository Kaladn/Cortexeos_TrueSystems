import re

log_content = """Starting memory insertion from: /home/ubuntu/gpu_prototype_cuda/final_vectorized_training_data.jsonl
Processed 10000 entries. Flushed to CortexCube. Current unique voxels activated: 320000
Processed 20000 entries. Flushed to CortexCube. Current unique voxels activated: 640000
Processed 30000 entries. Flushed to CortexCube. Current unique voxels activated: 960000
Processed 40000 entries. Flushed to CortexCube. Current unique voxels activated: 1280000
Processed 50000 entries. Flushed to CortexCube. Current unique voxels activated: 1600000
Processed 60000 entries. Flushed to CortexCube. Current unique voxels activated: 1920000
Processed 70000 entries. Flushed to CortexCube. Current unique voxels activated: 2240000
Processed 80000 entries. Flushed to CortexCube. Current unique voxels activated: 2560000
Processed 90000 entries. Flushed to CortexCube. Current unique voxels activated: 2880000
Processed 100000 entries. Flushed to CortexCube. Current unique voxels activated: 3200000
Processed 110000 entries. Flushed to CortexCube. Current unique voxels activated: 3520000
Processed 120000 entries. Flushed to CortexCube. Current unique voxels activated: 3840000
Processed 130000 entries. Flushed to CortexCube. Current unique voxels activated: 4160000
Processed 140000 entries. Flushed to CortexCube. Current unique voxels activated: 4480000
Processed 150000 entries. Flushed to CortexCube. Current unique voxels activated: 4800000
Processed 160000 entries. Flushed to CortexCube. Current unique voxels activated: 5120000
Processed 170000 entries. Flushed to CortexCube. Current unique voxels activated: 5440000
Processed 180000 entries. Flushed to CortexCube. Current unique voxels activated: 5760000
Processed 190000 entries. Flushed to CortexCube. Current unique voxels activated: 6080000
Processed 200000 entries. Flushed to CortexCube. Current unique voxels activated: 6400000
Processed 210000 entries. Flushed to CortexCube. Current unique voxels activated: 6720000
Processed 220000 entries. Flushed to CortexCube. Current unique voxels activated: 7040000
Processed 230000 entries. Flushed to CortexCube. Current unique voxels activated: 7360000
Processed 240000 entries. Flushed to CortexCube. Current unique voxels activated: 7680000
Processed 250000 entries. Flushed to CortexCube. Current unique voxels activated: 8000000
Processed 260000 entries. Flushed to CortexCube. Current unique voxels activated: 8320000
Processed 270000 entries. Flushed to CortexCube. Current unique voxels activated: 8640000
Processed 280000 entries. Flushed to CortexCube. Current unique voxels activated: 8960000
Processed 290000 entries. Flushed to CortexCube. Current unique voxels activated: 9280000
Processed 300000 entries. Flushed to CortexCube. Current unique voxels activated: 9600000
Processed 310000 entries. Flushed to CortexCube. Current unique voxels activated: 9920000
Processed 320000 entries. Flushed to CortexCube. Current unique voxels activated: 10240000
Processed 330000 entries. Flushed to CortexCube. Current unique voxels activated: 10560000
Processed 340000 entries. Flushed to CortexCube. Current unique voxels activated: 10880000
Processed 350000 entries. Flushed to CortexCube. Current unique voxels activated: 11200000
Processed 360000 entries. Flushed to CortexCube. Current unique voxels activated: 11520000
Processed 370000 entries. Flushed to CortexCube. Current unique voxels activated: 11840000
[WARN] Ignored out-of-bounds activation at (108, 124, 116)
[WARN] Ignored out-of-bounds activation at (20, 44, 76)
[WARN] Ignored out-of-bounds activation at (108, 44, 108)
[WARN] Ignored out-of-bounds activation at (116, 44, 68)
[WARN] Ignored out-of-bounds activation at (60, 92, 108)
[WARN] Ignored out-of-bounds activation at (100, 100, 12)
[WARN] Ignored out-of-bounds activation at (20, 12, 100)
[WARN] Ignored out-of-bounds activation at (84, 68, 76)
[WARN] Ignored out-of-bounds activation at (4, 52, 124)
[WARN] Ignored out-of-bounds activation at (52, 116, 76)
[WARN] Ignored out-of-bounds activation at (124, 100, 4)
[WARN] Ignored out-of-bounds activation at (60, 92, 52)
[WARN] Ignored out-of-bounds activation at (124, 100, 92)
[WARN] Ignored out-of-bounds activation at (68, 52, 4)
[WARN] Ignored out-of-bounds activation at (28, 20, 84)
[WARN] Ignored out-of-bounds activation at (20, 20, 76)
[WARN] Ignored out-of-bounds activation at (68, 44, 28)
[WARN] Ignored out-of-bounds activation at (20, 92, 36)
[WARN] Ignored out-of-bounds activation at (76, 108, 124)
[WARN] Ignored out-of-bounds activation at (116, 68, 12)
[WARN] Ignored out-of-bounds activation at (108, 84, 44)
[WARN] Ignored out-of-bounds activation at (36, 108, 108)
[WARN] Ignored out-of-bounds activation at (4, 4, 92)
[WARN] Ignored out-of-bounds activation at (84, 60, 20)
[WARN] Ignored out-of-bounds activation at (68, 92, 68)
[WARN] Ignored out-of-bounds activation at (12, 4, 108)
[WARN] Ignored out-of-bounds activation at (76, 4, 4)
[WARN] Ignored out-of-bounds activation at (4, 60, 108)
[WARN] Ignored out-of-bounds activation at (44, 76, 76)
[WARN] Ignored out-of-bounds activation at (108, 124, 116)
[WARN] Ignored out-of-bounds activation at (20, 44, 76)
[WARN] Ignored out-of-bounds activation at (108, 44, 108)
[WARN] Ignored out-of-bounds activation at (116, 44, 68)

--- Memory Insertion Summary ---
Total entries processed: 370105
Total voxel activations: 11843360
Total unique voxels activated: 11840000
Memory insertion complete.
"""

summary_lines = []
warning_count = 0

# Find the summary block
summary_block_started = False
for line in log_content.splitlines():
    if "--- Memory Insertion Summary ---" in line:
        summary_block_started = True
        continue
    if summary_block_started:
        if "Memory insertion complete." in line:
            summary_lines.append(line)
            break # End of summary block
        summary_lines.append(line)

# Count warnings
for line in log_content.splitlines():
    if "[WARN] Ignored out-of-bounds activation" in line:
        warning_count += 1

parsed_summary = {}
for line in summary_lines:
    if ":" in line:
        key, value = line.split(":", 1)
        parsed_summary[key.strip()] = value.strip()

final_summary_text = "Memory Insertion Run Summary:\n"
if parsed_summary.get("Total entries processed"):
    final_summary_text += f"- Total entries processed: {parsed_summary['Total entries processed']}\n"
if parsed_summary.get("Total voxel activations"):
    final_summary_text += f"- Total voxel activations: {parsed_summary['Total voxel activations']}\n"
if parsed_summary.get("Total unique voxels activated"):
    final_summary_text += f"- Total unique voxels activated: {parsed_summary['Total unique voxels activated']}\n"
final_summary_text += f"- Total out-of-bounds warnings: {warning_count}\n"
if parsed_summary.get("Memory insertion complete."):
     final_summary_text += f"- Status: {parsed_summary['Memory insertion complete.']}"

print(final_summary_text)

with open("/home/ubuntu/memory_insertion_summary.txt", "w") as f_out:
    f_out.write(final_summary_text)

