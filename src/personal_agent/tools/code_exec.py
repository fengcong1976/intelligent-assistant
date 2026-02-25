"""
Code Execution Tool
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .base import BaseTool, ToolResult, tool_registry
from ..config import settings


class CodeExecuteTool(BaseTool):
    name = "code_execute"
    description = "执行代码并返回结果"
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "要执行的代码"
            },
            "language": {
                "type": "string",
                "enum": ["python", "bash", "powershell"],
                "description": "编程语言"
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒）",
                "default": 30
            }
        },
        "required": ["code", "language"]
    }

    def _is_dangerous_command(self, code: str) -> bool:
        code_lower = code.lower()
        for cmd in settings.security.blocked_commands:
            if cmd in code_lower:
                return True
        return False

    async def execute(
        self,
        code: str,
        language: str,
        timeout: int = 30
    ) -> ToolResult:
        if self._is_dangerous_command(code):
            return ToolResult(
                success=False,
                output="",
                error="Code contains dangerous commands that are not allowed"
            )

        try:
            if language == "python":
                return await self._execute_python(code, timeout)
            elif language == "bash":
                return await self._execute_bash(code, timeout)
            elif language == "powershell":
                return await self._execute_powershell(code, timeout)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unsupported language: {language}"
                )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution timed out after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}"
            )

    async def _execute_python(self, code: str, timeout: int) -> ToolResult:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "python",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=output or "Execution completed successfully",
                    data={"return_code": process.returncode}
                )
            else:
                return ToolResult(
                    success=False,
                    output=output,
                    error=error or f"Process exited with code {process.returncode}"
                )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def _execute_bash(self, code: str, timeout: int) -> ToolResult:
        process = await asyncio.create_subprocess_shell(
            code,
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
            raise

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        if process.returncode == 0:
            return ToolResult(
                success=True,
                output=output or "Execution completed successfully",
                data={"return_code": process.returncode}
            )
        else:
            return ToolResult(
                success=False,
                output=output,
                error=error or f"Process exited with code {process.returncode}"
            )

    async def _execute_powershell(self, code: str, timeout: int) -> ToolResult:
        process = await asyncio.create_subprocess_exec(
            "powershell",
            "-Command",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        if process.returncode == 0:
            return ToolResult(
                success=True,
                output=output or "Execution completed successfully",
                data={"return_code": process.returncode}
            )
        else:
            return ToolResult(
                success=False,
                output=output,
                error=error or f"Process exited with code {process.returncode}"
            )


class ShellCommandTool(BaseTool):
    name = "shell_command"
    description = "执行Shell命令"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令"
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒）",
                "default": 30
            }
        },
        "required": ["command"]
    }

    def _is_dangerous_command(self, command: str) -> bool:
        command_lower = command.lower()
        for cmd in settings.security.blocked_commands:
            if cmd in command_lower:
                return True
        return False

    async def execute(self, command: str, timeout: int = 30) -> ToolResult:
        if self._is_dangerous_command(command):
            return ToolResult(
                success=False,
                output="",
                error="Command contains dangerous operations that are not allowed"
            )

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

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=output or "Command executed successfully",
                    data={"return_code": process.returncode}
                )
            else:
                return ToolResult(
                    success=False,
                    output=output,
                    error=error or f"Command exited with code {process.returncode}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command execution failed: {str(e)}"
            )


def register_code_tools():
    tool_registry.register(CodeExecuteTool())
    tool_registry.register(ShellCommandTool())
