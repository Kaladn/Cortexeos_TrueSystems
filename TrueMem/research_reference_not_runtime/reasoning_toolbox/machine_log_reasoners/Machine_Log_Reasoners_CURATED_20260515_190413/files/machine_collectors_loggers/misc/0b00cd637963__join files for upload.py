# combine_files.py
#
# This script automates the process of combining all necessary project files
# into a single text file for analysis by an AI.
# It recursively scans the project directory, finds all .py and .md files,
# and formats them with the specific delimiters required for parsing.

import os

def combine_project_files(root_directory, output_filename):
    """
    Scans a directory, combines all .py and .md files into one file,
    and formats each with a specific header and footer.

    Args:
        root_directory (str): The path to the root of the project.
        output_filename (str): The name of the combined output file.
    """
    # Excluded directories, such as the Python virtual environment and cache.
    excluded_dirs = {'.venv', '__pycache__'}
    
    # Supported file extensions we want to capture.
    included_extensions = {'.py', '.md'}

    print(f"Starting file combination process in '{root_directory}'...")
    
    try:
        # Using 'w' mode to create the file or overwrite it if it already exists.
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            # os.walk will traverse the directory tree for us.
            for dirpath, dirnames, filenames in os.walk(root_directory):
                # This is a crucial step to prevent scanning excluded directories.
                # We modify dirnames in-place to stop os.walk from entering them.
                dirnames[:] = [d for d in dirnames if d not in excluded_dirs]

                print(f"Scanning directory: {dirpath}")
                
                for filename in filenames:
                    # Check if the file has one of the desired extensions.
                    if any(filename.lower().endswith(ext) for ext in included_extensions):
                        file_path = os.path.join(dirpath, filename)
                        
                        # --- IMPORTANT: Create the relative path ---
                        # This creates the path like 'phase1/context_engine.py'
                        # which is critical for the AI to understand the structure.
                        relative_path = os.path.relpath(file_path, root_directory)
                        
                        # Use forward slashes for cross-platform compatibility.
                        relative_path = relative_path.replace('\\', '/')
                        
                        print(f"  > Processing and adding: {relative_path}")
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                                content = infile.read()
                                
                                # --- Write the formatted block to the output file ---
                                outfile.write(f"# >>>>> BEGIN CORTEXOS FILE: {relative_path} <<<<<\n")
                                outfile.write(content)
                                # Ensure there's a newline at the end of the content
                                if not content.endswith('\n'):
                                    outfile.write('\n')
                                outfile.write(f"# >>>>> END CORTEXOS FILE: {relative_path} <<<<<\n\n")
                                
                        except Exception as e:
                            print(f"    ! Error reading {file_path}: {e}")

    except Exception as e:
        print(f"An error occurred during the file writing process: {e}")
        return

    print(f"\nProcess complete. All files have been combined into '{output_filename}'.")

# --- SCRIPT EXECUTION ---
if __name__ == "__main__":
    # The script will run in the directory where it is located.
    project_root = os.getcwd() 
    output_file = "CortexOS_Combined.txt"
    combine_project_files(project_root, output_file)
