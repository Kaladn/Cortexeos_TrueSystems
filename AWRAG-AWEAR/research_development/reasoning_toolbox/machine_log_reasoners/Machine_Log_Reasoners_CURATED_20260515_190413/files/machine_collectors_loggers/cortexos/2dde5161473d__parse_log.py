import re
import sys

def parse_log_file(log_file_path):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
    except FileNotFoundError:
        return f"Error: Log file not found at {log_file_path}"

    summary_lines_data = []
    warning_count = 0
    summary_block_started = False

    # Extract summary block
    for line in log_content.splitlines():
        if "--- Memory Insertion Summary ---" in line:
            summary_block_started = True
            continue 
        if summary_block_started:
            if "Memory insertion complete." in line:
                summary_lines_data.append(line) 
                break 
            summary_lines_data.append(line)
    
    # Count warnings
    for line in log_content.splitlines():
        if "[WARN] Ignored out-of-bounds activation" in line:
            warning_count += 1

    parsed_summary = {}
    for line_data in summary_lines_data:
        if ":" in line_data:
            key, value = line_data.split(":", 1)
            parsed_summary[key.strip()] = value.strip()
        elif "Memory insertion complete." in line_data: 
             parsed_summary["Status"] = line_data.strip()

    final_summary_text = "Memory Insertion Run Summary:\n"
    if parsed_summary.get("Total entries processed"):
        final_summary_text += f"- Total entries processed: {parsed_summary['Total entries processed']}\n"
    else:
        final_summary_text += "- Total entries processed: Not found in log\n"
        
    if parsed_summary.get("Total voxel activations"):
        final_summary_text += f"- Total voxel activations: {parsed_summary['Total voxel activations']}\n"
    else:
        final_summary_text += "- Total voxel activations: Not found in log\n"

    if parsed_summary.get("Total unique voxels activated"):
        final_summary_text += f"- Total unique voxels activated: {parsed_summary['Total unique voxels activated']}\n"
    else:
        final_summary_text += "- Total unique voxels activated: Not found in log\n"
        
    final_summary_text += f"- Total out-of-bounds warnings: {warning_count}\n"
    
    if parsed_summary.get("Status"):
         final_summary_text += f"- Status: {parsed_summary['Status']}\n"
    elif "Memory insertion complete." in parsed_summary.values():
        final_summary_text += f"- Status: Memory insertion complete.\n"
    else:
        final_summary_text += "- Status: Not found in log\n"

    return final_summary_text

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python parse_log.py <input_log_file> <output_summary_file>")
        sys.exit(1)
    
    input_log = sys.argv[1]
    output_summary_file = sys.argv[2]
    
    summary_text_result = parse_log_file(input_log)
    
    print("--- Parsed Summary ---")
    print(summary_text_result)
    print("----------------------")

    with open(output_summary_file, "w", encoding='utf-8') as f_out:
        f_out.write(summary_text_result)
    print(f"Summary written to {output_summary_file}")

