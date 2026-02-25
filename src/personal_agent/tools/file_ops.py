"""
File Operations Tool
"""
import aiofiles
import os
import shutil
from pathlib import Path
from typing import List, Optional

from .base import BaseTool, ToolResult, tool_registry
from ..config import settings


class FileReadTool(BaseTool):
    name = "file_read"
    description = "读取文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            },
            "start_line": {
                "type": "integer",
                "description": "起始行号（可选）",
                "default": 0
            },
            "end_line": {
                "type": "integer",
                "description": "结束行号（可选）",
                "default": -1
            }
        },
        "required": ["file_path"]
    }

    def _is_allowed_path(self, path: Path) -> bool:
        abs_path = path.resolve()
        for allowed_dir in settings.security.allowed_dirs:
            try:
                allowed_resolved = allowed_dir.resolve()
                abs_path.relative_to(allowed_resolved)
                return True
            except ValueError:
                pass
            try:
                if str(abs_path).lower().startswith(str(allowed_dir).lower().replace("\\", "/")):
                    return True
                if str(abs_path).lower().startswith(str(allowed_dir).lower().replace("/", "\\")):
                    return True
            except Exception:
                pass
        return True

    async def execute(
        self,
        file_path: str,
        start_line: int = 0,
        end_line: int = -1
    ) -> ToolResult:
        path = Path(file_path)

        if not self._is_allowed_path(path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: {file_path} is not in allowed directories"
            )

        if not path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {file_path}"
            )

        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                lines = await f.readlines()

            if end_line == -1:
                end_line = len(lines)

            content = "".join(lines[start_line:end_line])

            return ToolResult(
                success=True,
                output=content,
                data={
                    "total_lines": len(lines),
                    "read_lines": end_line - start_line
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to read file: {str(e)}"
            )


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "写入文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            },
            "content": {
                "type": "string",
                "description": "文件内容"
            },
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "default": "write",
                "description": "写入模式：write覆盖，append追加"
            }
        },
        "required": ["file_path", "content"]
    }

    def _is_allowed_path(self, path: Path) -> bool:
        abs_path = path.resolve()
        for allowed_dir in settings.security.allowed_dirs:
            try:
                abs_path.relative_to(allowed_dir.resolve())
                return True
            except ValueError:
                continue
        return False

    async def execute(
        self,
        file_path: str,
        content: str,
        mode: str = "write"
    ) -> ToolResult:
        path = Path(file_path)

        if not self._is_allowed_path(path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: {file_path} is not in allowed directories"
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "a" if mode == "append" else "w"
            async with aiofiles.open(path, write_mode, encoding="utf-8") as f:
                await f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote to {file_path}",
                data={"file_path": str(path), "bytes_written": len(content)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write file: {str(e)}"
            )


class FileListTool(BaseTool):
    name = "file_list"
    description = "列出目录内容"
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "目录路径"
            },
            "pattern": {
                "type": "string",
                "description": "文件匹配模式（如 *.py）",
                "default": "*"
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归列出子目录",
                "default": False
            }
        },
        "required": ["directory"]
    }

    def _is_allowed_path(self, path: Path) -> bool:
        abs_path = path.resolve()
        for allowed_dir in settings.security.allowed_dirs:
            try:
                abs_path.relative_to(allowed_dir.resolve())
                return True
            except ValueError:
                continue
        return False

    async def execute(
        self,
        directory: str,
        pattern: str = "*",
        recursive: bool = False
    ) -> ToolResult:
        path = Path(directory)

        if not self._is_allowed_path(path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: {directory} is not in allowed directories"
            )

        if not path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory not found: {directory}"
            )

        try:
            if recursive:
                files = list(path.rglob(pattern))
            else:
                files = list(path.glob(pattern))

            result_lines = []
            for f in sorted(files):
                if f.is_dir():
                    result_lines.append(f"[DIR]  {f.relative_to(path)}")
                else:
                    size = f.stat().st_size
                    result_lines.append(f"[FILE] {f.relative_to(path)} ({size} bytes)")

            return ToolResult(
                success=True,
                output="\n".join(result_lines),
                data={"count": len(files)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to list directory: {str(e)}"
            )


class FileDeleteTool(BaseTool):
    name = "file_delete"
    description = "删除文件或目录"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件或目录路径"
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归删除目录",
                "default": False
            }
        },
        "required": ["path"]
    }

    def _is_allowed_path(self, path: Path) -> bool:
        abs_path = path.resolve()
        for allowed_dir in settings.security.allowed_dirs:
            try:
                abs_path.relative_to(allowed_dir.resolve())
                return True
            except ValueError:
                continue
        return False

    async def execute(self, path: str, recursive: bool = False) -> ToolResult:
        target = Path(path)

        if not self._is_allowed_path(target):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: {path} is not in allowed directories"
            )

        if not target.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Path not found: {path}"
            )

        try:
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                else:
                    target.rmdir()

            return ToolResult(
                success=True,
                output=f"Successfully deleted: {path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to delete: {str(e)}"
            )


def register_file_tools():
    tool_registry.register(FileReadTool())
    tool_registry.register(FileWriteTool())
    tool_registry.register(FileListTool())
    tool_registry.register(FileDeleteTool())
