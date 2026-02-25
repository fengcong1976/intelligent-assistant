"""
Shell Command Tool - Execute shell commands safely
"""
import asyncio
import logging
import re
from typing import Optional
from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

DANGEROUS_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"dd\s+if=/dev/zero",
    r"dd\s+if=/dev/null",
    r"mkfs",
    r"fdisk",
    r":\(\)\s*\{\s*:\|:&\s*\}",
    r">\s*/dev/sd[a-z]",
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+.*\s+/",
    r"wget.*\|\s*bash",
    r"curl.*\|\s*bash",
    r"eval\s+.*\$\(curl",
    r"eval\s+.*\$\(wget",
]

DANGEROUS_PATTERNS = [
    r"format\s+[a-z]:",
    r"del\s+/[sS]\s+[a-zA-Z]:",
    r"rmdir\s+/[sS]\s+[a-zA-Z]:",
]


class ShellTool(BaseTool):
    name = "execute_shell_command"
    description = (
        "Execute a shell command on the local machine. "
        "Use this to list files, read content, check system status, or run scripts. "
        "Supports Windows PowerShell and CMD commands."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute (e.g., 'dir', 'Get-Process', 'whoami')."
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60, max: 300).",
                "default": 60
            },
            "confirm_dangerous": {
                "type": "boolean",
                "description": "Set to true if user confirmed execution of potentially dangerous command.",
                "default": False
            }
        },
        "required": ["command"]
    }

    def __init__(self):
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _is_dangerous_command(self, command: str) -> tuple[bool, str]:
        """Check if command is dangerous"""
        command_lower = command.lower()
        
        for pattern in DANGEROUS_COMMANDS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return True, f"Command matches dangerous pattern: {pattern}"
        
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return True, f"Command matches dangerous pattern: {pattern}"
        
        dangerous_keywords = [
            ("format", "Disk formatting"),
            ("del /s", "Recursive delete"),
            ("rmdir /s", "Recursive directory removal"),
            ("shutdown", "System shutdown"),
            ("restart", "System restart"),
        ]
        
        for keyword, reason in dangerous_keywords:
            if keyword in command_lower:
                return True, f"Potentially dangerous: {reason}"
        
        return False, ""

    async def execute(self, command: str, timeout: int = 60, confirm_dangerous: bool = False) -> ToolResult:
        """Execute shell command"""
        is_dangerous, danger_reason = self._is_dangerous_command(command)
        
        if is_dangerous and not confirm_dangerous:
            return ToolResult(
                success=False,
                output="",
                error=f"⚠️ Dangerous command blocked: {danger_reason}\n"
                      f"If you really want to execute this command, please confirm by saying 'yes, execute it'."
            )
        
        timeout = min(max(timeout, 1), 300)
        
        if self._progress_callback:
            await self._progress_callback(f"Executing: {command}")
        
        logger.info(f"Executing shell command: {command}")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds"
                )
            
            output = stdout.decode('utf-8', errors='replace')
            error_output = stderr.decode('utf-8', errors='replace')
            
            if process.returncode == 0:
                result_output = output if output else "Command executed successfully (no output)"
                if error_output and not output:
                    result_output = f"Output: {error_output}"
                elif error_output:
                    result_output = f"{output}\nStderr: {error_output}"
                
                return ToolResult(
                    success=True,
                    output=result_output,
                    data={
                        'returncode': process.returncode,
                        'stdout': output,
                        'stderr': error_output
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command failed with exit code {process.returncode}\n"
                          f"Error: {error_output if error_output else 'No error message'}",
                    data={
                        'returncode': process.returncode,
                        'stdout': output,
                        'stderr': error_output
                    }
                )
                
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {str(e)}"
            )


shell_tool = ShellTool()
