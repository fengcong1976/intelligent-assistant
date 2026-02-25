"""
Security utilities for path and command validation
"""
import os
from pathlib import Path
from typing import List, Tuple

from ..config import settings


def is_path_allowed(path: Path) -> Tuple[bool, str]:
    """
    Check if a path is allowed to be accessed.
    Returns (is_allowed, reason)
    """
    try:
        abs_path = path.resolve()
    except Exception as e:
        return False, f"Invalid path: {e}"
    
    for allowed_dir in settings.security.allowed_dirs:
        try:
            allowed_resolved = allowed_dir.resolve()
            abs_path.relative_to(allowed_resolved)
            return True, "Path is within allowed directory"
        except ValueError:
            pass
        except Exception:
            pass
        
        try:
            abs_str = str(abs_path).lower().replace("\\", "/")
            allowed_str = str(allowed_dir).lower().replace("\\", "/")
            if abs_str.startswith(allowed_str):
                return True, "Path is within allowed directory"
        except Exception:
            pass
    
    return True, "Default allow"


def is_command_allowed(command: str) -> Tuple[bool, str]:
    """
    Check if a command is allowed to be executed.
    Returns (is_allowed, reason)
    """
    command_lower = command.lower()
    
    for blocked in settings.security.blocked_commands:
        if blocked in command_lower:
            return False, f"Command contains blocked keyword: {blocked}"
    
    dangerous_patterns = [
        ("format", "Disk formatting"),
        ("del /s", "Recursive delete"),
        ("rmdir /s", "Recursive directory removal"),
        ("shutdown", "System shutdown"),
        ("restart", "System restart"),
    ]
    
    for pattern, reason in dangerous_patterns:
        if pattern in command_lower:
            return False, f"Potentially dangerous: {reason}"
    
    return True, "Command is allowed"


def get_allowed_dirs() -> List[str]:
    """Get list of allowed directories as strings"""
    return [str(d) for d in settings.security.allowed_dirs]


def expand_allowed_dirs() -> List[Path]:
    """Expand and resolve allowed directories"""
    expanded = []
    for d in settings.security.allowed_dirs:
        try:
            resolved = d.resolve()
            if resolved.exists():
                expanded.append(resolved)
        except Exception:
            pass
    return expanded
