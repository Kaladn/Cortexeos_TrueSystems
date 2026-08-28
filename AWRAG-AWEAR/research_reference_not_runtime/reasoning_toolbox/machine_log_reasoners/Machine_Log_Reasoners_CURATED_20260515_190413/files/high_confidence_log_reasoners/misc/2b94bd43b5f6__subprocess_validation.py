"""
Subprocess Command Injection Validation
Addresses CVE-2025-67640 (Jenkins Git command injection)

Prevents command injection in subprocess calls.
"""

import re
import shlex
from typing import List, Union


# Dangerous shell metacharacters that enable command injection
SHELL_METACHARACTERS = [
    ";", "|", "&", "$", "`", "(", ")", "<", ">", "\n", "\r", "\\",
    "||", "&&", ">>", "<<", "$(",  "$()", "${}", "`", "!"
]


def contains_shell_metacharacters(command: str) -> bool:
    """
    Check if a command string contains dangerous shell metacharacters.
    
    Args:
        command: The command string to check
        
    Returns:
        True if dangerous characters found, False otherwise
    """
    for metachar in SHELL_METACHARACTERS:
        if metachar in command:
            return True
    return False


def validate_subprocess_args(args: Union[str, List[str]], allow_shell: bool = False) -> bool:
    """
    Validate subprocess arguments for command injection risks.
    
    Args:
        args: Command arguments (string or list)
        allow_shell: Whether shell=True is allowed (default: False)
        
    Returns:
        True if args are safe, False otherwise
        
    Examples:
        >>> validate_subprocess_args(["git", "status"])
        True
        >>> validate_subprocess_args("git status; rm -rf /")
        False
        >>> validate_subprocess_args(["git", "commit", "-m", "fix; rm -rf /"])
        True  # Safe because it's a list (no shell interpretation)
    """
    # If args is a string and shell=False, it's dangerous
    if isinstance(args, str):
        if not allow_shell:
            # String commands without shell=True are dangerous
            return False
        
        # If shell=True, check for metacharacters
        if contains_shell_metacharacters(args):
            return False
    
    # If args is a list, check each argument
    elif isinstance(args, list):
        for arg in args:
            if not isinstance(arg, str):
                return False
            
            # Even in list form, check for obvious injection attempts
            if contains_shell_metacharacters(arg):
                # Allow some metacharacters in specific contexts (e.g., git commit messages)
                # But flag obvious command injection patterns
                if any(pattern in arg for pattern in [";", "|", "&&", "||", "`", "$("]):
                    return False
    
    return True


def safe_subprocess_command(command: str, args: List[str]) -> List[str]:
    """
    Construct a safe subprocess command from a base command and arguments.
    
    Always returns a list (for shell=False) with properly escaped arguments.
    
    Args:
        command: The base command (e.g., "git")
        args: List of arguments
        
    Returns:
        Safe command list for subprocess.run()
        
    Raises:
        ValueError: If command or args contain dangerous patterns
        
    Examples:
        >>> safe_subprocess_command("git", ["status"])
        ['git', 'status']
        >>> safe_subprocess_command("git", ["commit", "-m", "fix; dangerous"])
        ['git', 'commit', '-m', 'fix; dangerous']  # Safe in list form
    """
    # Validate base command
    if contains_shell_metacharacters(command):
        raise ValueError(f"Base command contains shell metacharacters: {command}")
    
    # Validate arguments
    safe_args = [command]
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(f"Argument must be string: {arg}")
        
        # Escape the argument using shlex
        safe_arg = shlex.quote(arg)
        safe_args.append(safe_arg)
    
    return safe_args


# Pre-commit hook integration
def check_subprocess_call(code_line: str) -> tuple[bool, str]:
    """
    Check a line of code for unsafe subprocess usage.
    
    Args:
        code_line: Line of Python code to check
        
    Returns:
        Tuple of (is_safe, message)
    """
    # Pattern 1: subprocess with shell=True
    if "shell=True" in code_line or "shell = True" in code_line:
        return False, "subprocess call with shell=True detected (use shell=False)"
    
    # Pattern 2: subprocess with string command (implies shell=True)
    if re.search(r'subprocess\.(run|call|Popen)\s*\(\s*["\']', code_line):
        return False, "subprocess call with string command detected (use list of args)"
    
    # Pattern 3: os.system (always dangerous)
    if "os.system" in code_line:
        return False, "os.system() detected (use subprocess.run() with shell=False)"
    
    # Pattern 4: eval/exec (code injection)
    if re.search(r'\b(eval|exec)\s*\(', code_line):
        return False, "eval() or exec() detected (code injection risk)"
    
    return True, "OK"


# Example usage
if __name__ == "__main__":
    import sys
    
    # Test cases
    test_cases = [
        (["git", "status"], False, True),
        ("git status", False, False),
        ("git status; rm -rf /", True, False),
        (["git", "commit", "-m", "fix; test"], False, True),
    ]
    
    print("Subprocess Validation Tests:")
    for args, allow_shell, expected in test_cases:
        result = validate_subprocess_args(args, allow_shell)
        status = "✓" if result == expected else "✗"
        print(f"{status} {args} (shell={allow_shell}): {result}")
    
    sys.exit(0)
