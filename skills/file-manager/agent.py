"""
File Manager Skill Executor
OpenClaw compatible skill implementation
"""
import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List


async def list_directory(path: str, recursive: bool = False) -> Dict[str, Any]:
    """List directory contents"""
    try:
        target = Path(path)
        if not target.exists():
            return {"success": False, "error": f"路径不存在: {path}"}
        
        if not target.is_dir():
            return {"success": False, "error": f"不是目录: {path}"}
        
        items = []
        
        if recursive:
            for item in target.rglob("*"):
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0
                })
        else:
            for item in target.iterdir():
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0
                })
        
        return {
            "success": True,
            "path": str(target),
            "count": len(items),
            "items": items[:100],
            "truncated": len(items) > 100
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_directory(path: str) -> Dict[str, Any]:
    """Create a directory"""
    try:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "path": str(target),
            "message": f"文件夹创建成功: {target}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def rename_item(old_path: str, new_name: str) -> Dict[str, Any]:
    """Rename a file or directory"""
    try:
        old = Path(old_path)
        if not old.exists():
            return {"success": False, "error": f"路径不存在: {old_path}"}
        
        new_path = old.parent / new_name
        
        if new_path.exists():
            return {"success": False, "error": f"目标已存在: {new_path}"}
        
        old.rename(new_path)
        
        return {
            "success": True,
            "old_path": str(old),
            "new_path": str(new_path),
            "message": f"重命名成功: {old.name} -> {new_name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def move_item(source: str, destination: str) -> Dict[str, Any]:
    """Move a file or directory"""
    try:
        src = Path(source)
        dst = Path(destination)
        
        if not src.exists():
            return {"success": False, "error": f"源路径不存在: {source}"}
        
        if dst.exists() and dst.is_file():
            return {"success": False, "error": f"目标已存在: {destination}"}
        
        if dst.is_dir():
            dst = dst / src.name
        
        shutil.move(str(src), str(dst))
        
        return {
            "success": True,
            "source": str(src),
            "destination": str(dst),
            "message": f"移动成功: {src} -> {dst}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def copy_item(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file or directory"""
    try:
        src = Path(source)
        dst = Path(destination)
        
        if not src.exists():
            return {"success": False, "error": f"源路径不存在: {source}"}
        
        if src.is_dir():
            if dst.is_dir():
                dst = dst / src.name
            shutil.copytree(str(src), str(dst))
        else:
            if dst.is_dir():
                dst = dst / src.name
            shutil.copy2(str(src), str(dst))
        
        return {
            "success": True,
            "source": str(src),
            "destination": str(dst),
            "message": f"复制成功: {src} -> {dst}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_item(path: str, force: bool = False) -> Dict[str, Any]:
    """Delete a file or directory"""
    try:
        target = Path(path)
        
        if not target.exists():
            return {"success": False, "error": f"路径不存在: {path}"}
        
        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()
        
        return {
            "success": True,
            "path": str(target),
            "message": f"删除成功: {target}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_files(path: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
    """Search for files matching a pattern"""
    try:
        target = Path(path)
        
        if not target.exists():
            return {"success": False, "error": f"路径不存在: {path}"}
        
        results = []
        
        if recursive:
            items = target.rglob(pattern)
        else:
            items = target.glob(pattern)
        
        for item in items:
            results.append({
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return {
            "success": True,
            "path": str(target),
            "pattern": pattern,
            "count": len(results),
            "results": results[:100],
            "truncated": len(results) > 100
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_item_info(path: str) -> Dict[str, Any]:
    """Get information about a file or directory"""
    try:
        target = Path(path)
        
        if not target.exists():
            return {"success": False, "error": f"路径不存在: {path}"}
        
        stat = target.stat()
        
        return {
            "success": True,
            "name": target.name,
            "path": str(target),
            "type": "directory" if target.is_dir() else "file",
            "size": stat.st_size,
            "size_human": _format_size(stat.st_size),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _format_size(size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


async def execute(
    action: str,
    path: str = "",
    source: str = "",
    destination: str = "",
    new_name: str = "",
    pattern: str = "",
    recursive: bool = False,
    force: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Main entry point for file manager skill
    
    Args:
        action: 操作类型 (list, create, rename, move, copy, delete, search, info)
        path: 目标路径
        source: 源路径 (用于 move, copy)
        destination: 目标路径 (用于 move, copy)
        new_name: 新名称 (用于 rename)
        pattern: 搜索模式 (用于 search)
        recursive: 是否递归
        force: 是否强制执行
    """
    action = action.lower()
    
    if action == "list":
        return await list_directory(path, recursive)
    elif action == "create":
        return await create_directory(path)
    elif action == "rename":
        return await rename_item(path, new_name)
    elif action == "move":
        return await move_item(source, destination)
    elif action == "copy":
        return await copy_item(source, destination)
    elif action == "delete":
        return await delete_item(path, force)
    elif action == "search":
        return await search_files(path, pattern, recursive)
    elif action == "info":
        return await get_item_info(path)
    else:
        return {
            "success": False,
            "error": f"未知操作: {action}。支持的操作: list, create, rename, move, copy, delete, search, info"
        }


if __name__ == "__main__":
    import asyncio
    
    # Test the skill
    async def test():
        # Test list
        result = await execute(action="list", path=".")
        print(f"List result: {result['success']}, count: {result.get('count', 0)}")
        
        # Test create and delete
        result = await execute(action="create", path="./test_folder")
        print(f"Create result: {result}")
        
        result = await execute(action="delete", path="./test_folder")
        print(f"Delete result: {result}")
    
    asyncio.run(test())
