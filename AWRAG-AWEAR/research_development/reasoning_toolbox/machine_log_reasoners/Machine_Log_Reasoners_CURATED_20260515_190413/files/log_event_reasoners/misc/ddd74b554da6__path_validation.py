"""
Path Traversal Validation
Addresses CVE-2025-67720 (Pyrofork) and CVE-2025-67643 (Jenkins)

Prevents ../../../etc/passwd style attacks on file operations.
"""

import os
from pathlib import Path
from typing import Union


def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """
    Validate that a path is within the allowed base directory.
    
    Prevents path traversal attacks by ensuring the resolved absolute path
    stays within the base directory boundaries.
    
    Args:
        path: The path to validate (can be relative or absolute)
        base_dir: The base directory that path must stay within
        
    Returns:
        True if path is safe (within base_dir), False otherwise
        
    Examples:
        >>> is_safe_path("data/file.txt", "/home/user/project")
        True
        >>> is_safe_path("../../../etc/passwd", "/home/user/project")
        False
        >>> is_safe_path("/home/user/project/data/../file.txt", "/home/user/project")
        True
    """
    try:
        # Convert to Path objects and resolve to absolute paths
        path_obj = Path(path).resolve()
        base_obj = Path(base_dir).resolve()
        
        # Check if resolved path is relative to base directory
        # This handles symlinks, .., ., and other path tricks
        path_obj.relative_to(base_obj)
        return True
        
    except (ValueError, OSError):
        # ValueError: path is not relative to base_dir
        # OSError: path doesn't exist or permission denied
        return False


def sanitize_filename(filename: str) -> str:
    """
    Remove dangerous characters from filenames.
    
    Strips path separators and other dangerous characters that could
    be used for directory traversal or command injection.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename safe for file operations
        
    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        "etcpasswd"
        >>> sanitize_filename("file; rm -rf /")
        "file rm -rf "
    """
    # Remove path separators
    filename = filename.replace("/", "").replace("\\", "")
    
    # Remove null bytes (can truncate paths in C)
    filename = filename.replace("\x00", "")
    
    # Remove dangerous shell characters
    dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        filename = filename.replace(char, "")
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")
    
    return filename


def validate_file_operation(filepath: Union[str, Path], base_dir: Union[str, Path]) -> Path:
    """
    Validate and return a safe Path object for file operations.
    
    Combines path safety check with filename sanitization.
    Raises exception if path is unsafe.
    
    Args:
        filepath: The file path to validate
        base_dir: The base directory for operations
        
    Returns:
        Validated Path object
        
    Raises:
        ValueError: If path is outside base_dir or contains dangerous patterns
        
    Examples:
        >>> validate_file_operation("data/file.txt", "/home/user/project")
        PosixPath('/home/user/project/data/file.txt')
        >>> validate_file_operation("../../../etc/passwd", "/home/user/project")
        Traceback (most recent call last):
        ...
        ValueError: Path traversal detected: path is outside base directory
    """
    # Convert to Path object
    path_obj = Path(filepath)
    
    # Sanitize the filename component
    sanitized_name = sanitize_filename(path_obj.name)
    if not sanitized_name:
        raise ValueError(f"Invalid filename after sanitization: {path_obj.name}")
    
    # Reconstruct path with sanitized filename
    if path_obj.parent != Path("."):
        safe_path = path_obj.parent / sanitized_name
    else:
        safe_path = Path(sanitized_name)
    
    # Validate against base directory
    if not is_safe_path(safe_path, base_dir):
        raise ValueError(
            f"Path traversal detected: {safe_path} is outside base directory {base_dir}"
        )
    
    return Path(base_dir) / safe_path


# Example usage in pre-commit hook
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python path_validation.py <filepath> <base_dir>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    base_dir = sys.argv[2]
    
    try:
        safe_path = validate_file_operation(filepath, base_dir)
        print(f"✓ Safe path: {safe_path}")
        sys.exit(0)
    except ValueError as e:
        print(f"✗ Unsafe path: {e}", file=sys.stderr)
        sys.exit(1)
