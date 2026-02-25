"""
File Agent - 文件管理智能体
专门负责文件操作任务
"""
import os
import shutil
import platform
from pathlib import Path
from typing import Any, Dict, List
from loguru import logger

from ..base import BaseAgent, Task, Message


class FileAgent(BaseAgent):
    """
    文件管理智能体

    能力：
    - 文件/目录操作（创建、删除、移动、复制）
    - 文件搜索
    - 文件信息获取
    - 磁盘空间查询
    - 批量操作
    - 文件类型识别（支持扩展名和内容识别）
    - 文件内容分析（支持文本、JSON、Python、图片、PDF等）
    - 文件和目录统计
    """
    
    KEYWORD_MAPPINGS = {
        "磁盘空间": ("disk_space", {}),
        "磁盘使用": ("disk_space", {}),
        "C盘空间": ("disk_space", {"drive": "C"}),
        "D盘空间": ("disk_space", {"drive": "D"}),
    }
    
    def get_capabilities_description(self) -> str:
        """获取能力描述，用于LLM意图识别"""
        return """### file_agent (文件操作智能体)
- 文件搜索: 搜索文件，action=search, query=搜索关键词, path=搜索路径
- 文件复制: 复制文件，action=copy, source=源文件路径, target=目标文件路径
- 文件移动: 移动文件，action=move, source=源文件路径, target=目标文件路径
- 文件删除: 删除文件，action=delete, path=文件路径
- 磁盘空间查询: 查询磁盘空间，action=disk_space, path=磁盘路径
- 文件类型识别: 识别文件类型，action=identify_file_type, path=文件路径
- 文件内容分析: 分析文件内容，action=analyze_file, path=文件路径
- 文件统计: 统计文件和目录数量，action=get_file_statistics, path=目录路径
- 示例: "搜索桌面上的PDF文件" -> action=search, query="*.pdf", path="C:\\Users\\用户名\\Desktop"
- 示例: "复制文件到D盘" -> action=copy, source="C:\\path\\to\\file.txt", target="D:\\path\\to\\file.txt"
- 示例: "分析文件内容" -> action=analyze_file, path="C:\\path\\to\\file.txt"
"""
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """📁 文件操作智能体

功能：
- 文件搜索：根据关键词搜索文件
- 文件复制：复制文件到指定位置
- 文件移动：移动文件到指定位置
- 文件删除：删除指定文件
- 磁盘空间查询：查询磁盘空间使用情况
- 文件类型识别：识别文件类型（支持扩展名和内容识别）
- 文件内容分析：分析文件内容（支持文本、JSON、Python、图片、PDF等）
- 文件统计：统计文件和目录数量
- 批量文件操作：支持批量复制、移动、删除文件

使用方法：
- "搜索桌面上的PDF文件"
- "复制文件到D盘"
- "移动文件到桌面"
- "删除临时文件"
- "查询C盘空间"
- "分析文件内容"
- "识别文件类型"

参数说明：
- search: query=搜索关键词, path=搜索路径（可选）
- copy: source=源文件路径, target=目标文件路径
- move: source=源文件路径, target=目标文件路径
- delete: path=文件路径
- disk_space: path=磁盘路径（可选）
- identify_file_type: path=文件路径
- analyze_file: path=文件路径
- get_file_statistics: path=目录路径（可选）

注意：
- 支持绝对路径和相对路径
- 支持通配符搜索（如*.txt, *.pdf等）
- 文件内容分析支持多种文件类型
- 操作前会验证文件和目录是否存在
- 批量操作时会显示详细的操作结果
"""
    

    def __init__(self):
        super().__init__(
            name="file_agent",
            description="文件管理智能体 - 负责文件操作和管理"
        )

        self.register_capability(
            capability="find_file",
            description="在电脑上搜索文件。根据文件名或关键词查找文件位置。",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名或关键词"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索路径（可选），默认全盘搜索"
                    }
                },
                "required": ["filename"]
            },
            category="file"
        )
        
        self.register_capability(
            capability="disk_space",
            description="查询磁盘空间使用情况。查看指定磁盘的剩余空间和总容量。",
            parameters={
                "type": "object",
                "properties": {
                    "drive": {
                        "type": "string",
                        "description": "磁盘盘符，如'C'、'D'、'E'，不填则显示所有磁盘",
                        "default": ""
                    }
                },
                "required": []
            },
            category="file"
        )
        
        self.register_capability("file_management", "文件管理")
        self.register_capability("file_search", "文件搜索")
        self.register_capability("file_operation", "文件操作")
        self.register_capability("disk_management", "磁盘管理")
        self.register_capability("file_analysis", "文件分析")
        self.register_capability("file_type_recognition", "文件类型识别")

        self.operation_count = 0
        
        # 文件类型映射
        self.file_type_mappings = {
            # 文本文件
            ".txt": "text",
            ".md": "markdown",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".js": "javascript",
            ".py": "python",
            ".java": "java",
            ".c": "c",
            ".cpp": "c++",
            ".h": "header",
            ".cs": "c#",
            ".php": "php",
            ".rb": "ruby",
            ".go": "go",
            ".rust": "rust",
            # 图像文件
            ".jpg": "jpg",
            ".jpeg": "jpeg",
            ".png": "png",
            ".gif": "gif",
            ".bmp": "bmp",
            ".tiff": "tiff",
            ".svg": "svg",
            ".webp": "webp",
            # 文档文件
            ".doc": "word",
            ".docx": "word",
            ".xls": "excel",
            ".xlsx": "excel",
            ".ppt": "powerpoint",
            ".pptx": "powerpoint",
            ".pdf": "pdf",
            # 压缩文件
            ".zip": "zip",
            ".rar": "rar",
            ".7z": "7z",
            ".tar": "tar",
            ".gz": "gzip",
            # 音频文件
            ".mp3": "mp3",
            ".wav": "wav",
            ".aac": "aac",
            ".flac": "flac",
            ".ogg": "ogg",
            # 视频文件
            ".mp4": "mp4",
            ".avi": "avi",
            ".mkv": "mkv",
            ".mov": "mov",
            ".wmv": "wmv",
        }

        logger.info("📁 文件管理智能体已初始化")

    async def execute_task(self, task: Task) -> Any:
        """执行文件相关任务"""
        task_type = task.type
        params = task.params

        logger.info(f"📁 执行文件任务: {task_type}")

        try:
            if task_type == "file_operation":
                return await self._handle_file_operation(params)

            elif task_type in ["search_file", "find_file"]:
                return await self._handle_search_file(params)

            elif task_type == "get_file_info":
                return await self._handle_get_info(params)

            elif task_type == "disk_space":
                return await self._handle_disk_space(params)

            elif task_type == "list_drives":
                return await self._handle_list_drives(params)

            elif task_type == "largest_folder":
                return await self._handle_largest_folder(params)

            elif task_type == "search_files":
                return await self._handle_search_files(params)

            elif task_type == "count_files":
                return await self._handle_count_files(params)

            elif task_type == "natural_query":
                return await self._handle_natural_query(params)

            elif task_type == "batch_operation":
                return await self._handle_batch_operation(params)

            elif task_type == "analyze_file":
                return await self._handle_analyze_file(params)

            elif task_type == "recognize_file_type":
                return await self._handle_recognize_file_type(params)

            elif task_type == "general":
                return await self._handle_general(params)

            else:
                error_msg = f"❌ 不支持的文件操作: {task_type}"
                logger.warning(error_msg)
                return error_msg
        except Exception as e:
            error_msg = f"❌ 执行任务失败: {str(e)}"
            logger.error(error_msg)
            logger.exception("详细错误信息:")
            return error_msg
    
    async def _handle_general(self, params: Dict) -> str:
        """处理 general 类型任务，增强意图识别"""
        text = params.get("text", params.get("original_text", "")).lower()
        
        search_keywords = ["找", "搜索", "查找", "找一下", "找找", "在哪里", "哪个"]
        if any(kw in text for kw in search_keywords):
            search_text = text
            for kw in search_keywords:
                search_text = search_text.replace(kw, "")
            return await self._handle_search_file({"query": search_text.strip()})
        
        disk_keywords = ["磁盘", "空间", "容量", "多大", "剩余", "占用"]
        if any(kw in text for kw in disk_keywords):
            return await self._handle_disk_space({})
        
        list_keywords = ["列出", "显示", "有哪些", "看看"]
        drive_keywords = ["盘", "驱动器", "硬盘"]
        if any(kw in text for kw in list_keywords) and any(kw in text for kw in drive_keywords):
            return await self._handle_list_drives({})
        
        return f"❌ 无法识别的文件操作指令: {text}"

    async def _handle_file_operation(self, params: Dict) -> str:
        """处理文件操作"""
        operation = params.get("operation", "")
        source = params.get("source", "")
        destination = params.get("destination", "")

        logger.info(f"📁 文件操作: {operation} {source} -> {destination}")

        try:
            # 验证操作类型
            if not operation:
                error_msg = "❌ 操作类型不能为空"
                logger.warning(error_msg)
                return error_msg
            
            # 验证源路径
            if operation not in ["create_dir"] and not source:
                error_msg = "❌ 源路径不能为空"
                logger.warning(error_msg)
                return error_msg
            
            # 验证目标路径
            if operation in ["copy", "move"] and not destination:
                error_msg = "❌ 目标路径不能为空"
                logger.warning(error_msg)
                return error_msg
            
            # 执行操作
            if operation == "copy":
                if not os.path.exists(source):
                    error_msg = f"❌ 源文件/目录不存在: {source}"
                    logger.warning(error_msg)
                    return error_msg
                
                if os.path.isdir(source):
                    if os.path.exists(destination):
                        error_msg = f"❌ 目标目录已存在: {destination}"
                        logger.warning(error_msg)
                        return error_msg
                    shutil.copytree(source, destination)
                else:
                    if os.path.exists(destination) and os.path.isdir(destination):
                        destination = os.path.join(destination, os.path.basename(source))
                    shutil.copy2(source, destination)
                result = f"✅ 已复制: {source} -> {destination}"

            elif operation == "move":
                if not os.path.exists(source):
                    error_msg = f"❌ 源文件/目录不存在: {source}"
                    logger.warning(error_msg)
                    return error_msg
                
                shutil.move(source, destination)
                result = f"✅ 已移动: {source} -> {destination}"

            elif operation == "delete":
                if not os.path.exists(source):
                    error_msg = f"❌ 源文件/目录不存在: {source}"
                    logger.warning(error_msg)
                    return error_msg
                
                if os.path.isdir(source):
                    shutil.rmtree(source)
                else:
                    os.remove(source)
                result = f"✅ 已删除: {source}"

            elif operation == "create_dir":
                if os.path.exists(source):
                    result = f"⚠️ 目录已存在: {source}"
                    logger.warning(result)
                else:
                    os.makedirs(source, exist_ok=True)
                    result = f"✅ 已创建目录: {source}"

            else:
                error_msg = f"❌ 不支持的操作: {operation}"
                logger.warning(error_msg)
                return error_msg

            self.operation_count += 1
            logger.info(result)
            return result

        except Exception as e:
            error_msg = f"❌ 操作失败: {str(e)}"
            logger.error(f"❌ 文件操作失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_search_file(self, params: Dict) -> str:
        """搜索文件"""
        keyword = params.get("keyword", "") or params.get("filename", "")
        path = params.get("path", ".")
        file_type = params.get("type", "")
        
        if path and len(path) == 2 and path[1] == ':':
            path = path + "\\"
        
        if not path or path == ".":
            path = os.path.expanduser("~")

        logger.info(f"🔍 搜索文件: {keyword} in {path}")

        try:
            if not os.path.exists(path):
                error_msg = f"❌ 搜索路径不存在: {path}"
                logger.warning(error_msg)
                return error_msg
            
            if not os.path.isdir(path):
                error_msg = f"❌ 搜索路径不是目录: {path}"
                logger.warning(error_msg)
                return error_msg
            
            import fnmatch
            
            results = []
            for root, dirs, files in os.walk(path):
                for file in files:
                    if '*' in keyword or '?' in keyword:
                        if fnmatch.fnmatch(file.lower(), keyword.lower()):
                            results.append(os.path.join(root, file))
                    elif keyword.lower() in file.lower():
                        if file_type and not file.endswith(file_type):
                            continue
                        results.append(os.path.join(root, file))

            if results:
                result_msg = f"🔍 找到 {len(results)} 个文件:\n" + "\n".join(results[:10])
                if len(results) > 10:
                    result_msg += f"\n... 还有 {len(results) - 10} 个文件"
                logger.info(f"🔍 搜索完成: 找到 {len(results)} 个文件")
                return result_msg
            else:
                logger.info(f"🔍 搜索完成: 未找到匹配的文件")
                return "🔍 未找到匹配的文件"

        except Exception as e:
            error_msg = f"❌ 搜索失败: {str(e)}"
            logger.error(f"❌ 搜索文件失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_get_info(self, params: Dict) -> str:
        """获取文件信息"""
        file_path = params.get("path", "")

        logger.info(f"ℹ️ 获取文件信息: {file_path}")

        try:
            # 验证文件路径
            if not file_path:
                error_msg = "❌ 文件路径不能为空"
                logger.warning(error_msg)
                return error_msg
            
            if not os.path.exists(file_path):
                error_msg = f"❌ 文件不存在: {file_path}"
                logger.warning(error_msg)
                return error_msg

            # 获取文件信息
            stat = os.stat(file_path)
            import datetime
            info = {
                "名称": os.path.basename(file_path),
                "路径": file_path,
                "大小": self._format_size(stat.st_size),
                "创建时间": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "修改时间": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "访问时间": datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
                "类型": "目录" if os.path.isdir(file_path) else "文件",
                "是否可读": str(os.access(file_path, os.R_OK)),
                "是否可写": str(os.access(file_path, os.W_OK)),
                "是否可执行": str(os.access(file_path, os.X_OK))
            }

            result = "ℹ️ 文件信息:\n\n"
            result += "\n".join([f"{k}: {v}" for k, v in info.items()])
            logger.info(f"ℹ️ 获取文件信息成功: {file_path}")
            return result

        except Exception as e:
            error_msg = f"❌ 获取信息失败: {str(e)}"
            logger.error(f"❌ 获取文件信息失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_batch_operation(self, params: Dict) -> str:
        """批量操作"""
        files = params.get("files", [])
        operation = params.get("operation", "")

        logger.info(f"📁 批量操作: {operation} {len(files)} 个文件")

        try:
            # 验证参数
            if not operation:
                error_msg = "❌ 操作类型不能为空"
                logger.warning(error_msg)
                return error_msg
            
            if not files:
                error_msg = "❌ 文件列表不能为空"
                logger.warning(error_msg)
                return error_msg
            
            # 执行批量操作
            results = []
            success_count = 0
            for file in files:
                params["source"] = file
                result = await self._handle_file_operation(params)
                results.append(result)
                if "✅" in result:
                    success_count += 1

            result_msg = f"✅ 批量操作完成: 成功 {success_count} 个，失败 {len(files) - success_count} 个\n\n"
            result_msg += "\n".join(results)
            logger.info(f"📁 批量操作完成: 成功 {success_count} 个，失败 {len(files) - success_count} 个")
            return result_msg
        except Exception as e:
            error_msg = f"❌ 批量操作失败: {str(e)}"
            logger.error(f"❌ 批量操作失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_disk_space(self, params: Dict) -> str:
        """查询磁盘空间"""
        drive = params.get("drive", params.get("path", ""))
        
        logger.info(f"💾 查询磁盘空间: {drive}")
        
        if platform.system() == "Windows":
            if not drive:
                drive = "C:"
            elif len(drive) == 1:
                drive = drive + ":"
            elif not drive.endswith(":") and not drive.endswith(":\\"):
                drive = drive[0] + ":"
        else:
            drive = drive or "/"
        
        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                total_free_bytes = ctypes.c_ulonglong(0)
                
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(drive),
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    ctypes.byref(total_free_bytes)
                )
                
                total_gb = total_bytes.value / (1024 ** 3)
                free_gb = free_bytes.value / (1024 ** 3)
                used_gb = total_gb - free_gb
                used_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
            else:
                stat = shutil.disk_usage(drive)
                total_gb = stat.total / (1024 ** 3)
                free_gb = stat.free / (1024 ** 3)
                used_gb = stat.used / (1024 ** 3)
                used_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
            
            result_msg = f"💾 磁盘空间 ({drive}):\n\n" \
                   f"📊 总容量: {total_gb:.2f} GB\n" \
                   f"📈 已使用: {used_gb:.2f} GB ({used_percent:.1f}%)\n" \
                   f"📉 可用空间: {free_gb:.2f} GB"
            logger.info(f"💾 磁盘空间查询成功: {drive}")
            return result_msg
        
        except Exception as e:
            error_msg = f"❌ 获取磁盘空间失败: {str(e)}"
            logger.error(f"❌ 获取磁盘空间失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_list_drives(self, params: Dict) -> str:
        """列出所有驱动器"""
        logger.info("💾 列出所有驱动器")
        
        try:
            if platform.system() == "Windows":
                drives = []
                import ctypes
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    if bitmask & 1:
                        drives.append(f"{letter}:")
                    bitmask >>= 1
                
                logger.info(f"💾 发现 {len(drives)} 个驱动器")
                
                result = "💾 系统驱动器:\n\n"
                for drive in drives:
                    try:
                        usage = shutil.disk_usage(drive)
                        total_gb = usage.total / (1024 ** 3)
                        free_gb = usage.free / (1024 ** 3)
                        result += f"📁 {drive} - 总: {total_gb:.1f} GB, 可用: {free_gb:.1f} GB\n"
                    except Exception as e:
                        logger.warning(f"无法访问驱动器 {drive}: {e}")
                        result += f"📁 {drive} - (无法访问)\n"
                logger.info("💾 驱动器列表获取成功")
                return result
            else:
                result = "💾 系统挂载点:\n\n"
                stat = shutil.disk_usage("/")
                total_gb = stat.total / (1024 ** 3)
                free_gb = stat.free / (1024 ** 3)
                result += f"📁 / - 总: {total_gb:.1f} GB, 可用: {free_gb:.1f} GB\n"
                logger.info("💾 挂载点信息获取成功")
                return result
        except Exception as e:
            error_msg = f"❌ 获取驱动器列表失败: {str(e)}"
            logger.error(f"❌ 获取驱动器列表失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_natural_query(self, params: Dict) -> str:
        """处理自然语言查询"""
        query = params.get("original_text", params.get("query", "")).lower()
        
        logger.info(f"🔍 处理自然语言查询: {query}")
        
        try:
            import re
            
            drive_match = re.search(r'([a-zA-Z])\s*盘|([a-zA-Z]):', query)
            drive = None
            if drive_match:
                drive = (drive_match.group(1) or drive_match.group(2)).upper() + ":"
                logger.debug(f"🔍 识别到驱动器: {drive}")
            
            if "磁盘空间" in query or ("空间" in query and "最大" not in query) or "容量" in query:
                logger.debug("🔍 识别为磁盘空间查询")
                if drive:
                    return await self._handle_disk_space({"drive": drive})
                else:
                    return await self._handle_list_drives({})
            
            if "驱动器" in query or "硬盘" in query or "磁盘" in query:
                logger.debug("🔍 识别为驱动器列表查询")
                return await self._handle_list_drives({})
            
            if "最大" in query and ("文件夹" in query or "目录" in query or "占用" in query):
                logger.debug("🔍 识别为最大文件夹查询")
                return await self._handle_largest_folder({"drive": drive} if drive else {})
            
            file_type_match = re.search(r'\.(mp3|mp4|avi|mkv|pdf|doc|docx|xls|xlsx|jpg|png|zip|rar|txt|exe|msi)', query, re.IGNORECASE)
            if file_type_match or "文件" in query or "个" in query:
                file_type = file_type_match.group(1).upper() if file_type_match else None
                logger.debug(f"🔍 识别为文件查询，文件类型: {file_type}")
                
                if "多少" in query or "计数" in query or "几个" in query:
                    logger.debug("🔍 识别为文件计数查询")
                    return await self._handle_count_files({"drive": drive, "file_type": file_type})
                
                if "搜索" in query or "查找" in query or "找" in query:
                    logger.debug("🔍 识别为文件搜索查询")
                    return await self._handle_search_files({"drive": drive, "file_type": file_type})
            
            error_msg = f"❌ 无法理解的查询: {query}"
            logger.warning(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ 处理自然语言查询失败: {str(e)}"
            logger.error(f"❌ 处理自然语言查询失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_largest_folder(self, params: Dict) -> str:
        """查找占用空间最大的文件夹"""
        drive = params.get("drive", "C:")
        
        logger.info(f"🔍 查找占用空间最大的文件夹: {drive}")
        
        if len(drive) == 1:
            drive = drive + ":"
        
        try:
            if not os.path.exists(drive):
                error_msg = f"❌ 驱动器不存在: {drive}"
                logger.warning(error_msg)
                return error_msg
            
            logger.info(f"🔍 扫描 {drive} 根目录下的文件夹大小...")
            
            folder_sizes = []
            
            for item in os.listdir(drive):
                item_path = os.path.join(drive, item)
                if os.path.isdir(item_path):
                    try:
                        total_size = 0
                        for root, dirs, files in os.walk(item_path):
                            for f in files:
                                try:
                                    total_size += os.path.getsize(os.path.join(root, f))
                                except Exception as e:
                                    logger.debug(f"无法获取文件大小 {os.path.join(root, f)}: {e}")
                                    pass
                        folder_sizes.append((item_path, total_size))
                    except Exception as e:
                        logger.debug(f"无法访问 {item_path}: {e}")
            
            if not folder_sizes:
                error_msg = f"❌ 无法扫描 {drive} 的文件夹"
                logger.warning(error_msg)
                return error_msg
            
            folder_sizes.sort(key=lambda x: x[1], reverse=True)
            
            result = f"📊 {drive} 占用空间最大的文件夹 TOP 10:\n\n"
            for i, (path, size) in enumerate(folder_sizes[:10], 1):
                size_gb = size / (1024 ** 3)
                size_mb = size / (1024 ** 2)
                if size_gb >= 1:
                    result += f"{i}. {path}\n   📁 {size_gb:.2f} GB\n"
                else:
                    result += f"{i}. {path}\n   📁 {size_mb:.2f} MB\n"
            
            logger.info(f"🔍 扫描完成，找到 {len(folder_sizes)} 个文件夹")
            return result
        
        except Exception as e:
            error_msg = f"❌ 扫描失败: {str(e)}"
            logger.error(f"❌ 扫描失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_search_files(self, params: Dict) -> str:
        """搜索文件"""
        drive = params.get("drive", "C:")
        file_type = params.get("file_type")
        keyword = params.get("keyword", "")
        max_results = params.get("max_results", 50)
        
        logger.info(f"🔍 搜索文件: {drive}, 类型: {file_type}, 关键词: {keyword}")
        
        if len(drive) == 1:
            drive = drive + ":"
        
        try:
            if not os.path.exists(drive):
                error_msg = f"❌ 驱动器不存在: {drive}"
                logger.warning(error_msg)
                return error_msg
            
            results = []
            extensions = [f".{file_type.lower()}"] if file_type else None
            
            for root, dirs, files in os.walk(drive):
                for f in files:
                    if extensions and not any(f.lower().endswith(ext) for ext in extensions):
                        continue
                    if keyword and keyword.lower() not in f.lower():
                        continue
                    results.append(os.path.join(root, f))
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
            
            if not results:
                error_msg = f"❌ 未找到匹配的文件"
                logger.info(error_msg)
                return error_msg
            
            result_str = f"🔍 找到 {len(results)} 个文件:\n\n"
            for i, path in enumerate(results[:20], 1):
                try:
                    size = os.path.getsize(path)
                    size_str = self._format_size(size)
                    result_str += f"{i}. {os.path.basename(path)}\n   📁 {path}\n   💾 {size_str}\n"
                except Exception as e:
                    logger.debug(f"无法获取文件大小 {path}: {e}")
                    result_str += f"{i}. {os.path.basename(path)}\n   📁 {path}\n"
            
            if len(results) > 20:
                result_str += f"\n... 还有 {len(results) - 20} 个文件"
            
            logger.info(f"🔍 搜索完成，找到 {len(results)} 个文件")
            return result_str
        
        except Exception as e:
            error_msg = f"❌ 搜索失败: {str(e)}"
            logger.error(f"❌ 搜索失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_count_files(self, params: Dict) -> str:
        """统计文件数量"""
        drive = params.get("drive", "C:")
        file_type = params.get("file_type")
        
        logger.info(f"🔢 统计文件: {drive}, 类型: {file_type}")
        
        if len(drive) == 1:
            drive = drive + ":"
        
        try:
            if not os.path.exists(drive):
                error_msg = f"❌ 驱动器不存在: {drive}"
                logger.warning(error_msg)
                return error_msg
            
            count = 0
            total_size = 0
            extensions = [f".{file_type.lower()}"] if file_type else None
            
            for root, dirs, files in os.walk(drive):
                for f in files:
                    if extensions and not any(f.lower().endswith(ext) for ext in extensions):
                        continue
                    count += 1
                    try:
                        total_size += os.path.getsize(os.path.join(root, f))
                    except Exception as e:
                        logger.debug(f"无法获取文件大小 {os.path.join(root, f)}: {e}")
                        pass
            
            type_str = f"{file_type} " if file_type else ""
            result = f"📊 {drive} 下共有 {count} 个{type_str}文件\n"
            result += f"💾 总大小: {self._format_size(total_size)}"
            
            logger.info(f"🔢 统计完成，找到 {count} 个{type_str}文件")
            return result
        
        except Exception as e:
            error_msg = f"❌ 统计失败: {str(e)}"
            logger.error(f"❌ 统计失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    def _recognize_file_type_by_extension(self, file_path: str) -> str:
        """根据文件扩展名识别文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        return self.file_type_mappings.get(ext, "unknown")

    def _recognize_file_type_by_content(self, file_path: str) -> str:
        """根据文件内容识别文件类型"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
            
            # 检查文件头
            if header.startswith(b'\xff\xd8'):
                return "jpg"
            elif header.startswith(b'\x89PNG'):
                return "png"
            elif header.startswith(b'GIF8'):
                return "gif"
            elif header.startswith(b'BM'):
                return "bmp"
            elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                return "webp"
            elif header.startswith(b'%PDF'):
                return "pdf"
            elif header.startswith(b'PK\x03\x04'):
                return "zip"
            elif header.startswith(b'Rar!'):
                return "rar"
            elif header.startswith(b'7z\xbc\xaf\x27\x1c'):
                return "7z"
            elif header.startswith(b'ID3'):
                return "mp3"
            elif header.startswith(b'RIFF') and header[8:12] == b'WAVE':
                return "wav"
            elif header.startswith(b'\x00\x00\x00') and header[4:8] == b'ftyp':
                return "mp4"
            elif header.startswith(b'\x1a\x45\xdf\xa3'):
                return "mkv"
            elif header.startswith(b'DOS\s+MODE'):
                return "exe"
            elif header.startswith(b'#!'):
                return "script"
            elif all(32 <= c <= 126 or c in (9, 10, 13) for c in header if c):
                return "text"
            else:
                return "unknown"
        except Exception as e:
            logger.debug(f"无法根据内容识别文件类型: {e}")
            return "unknown"

    async def _handle_recognize_file_type(self, params: Dict) -> str:
        """识别文件类型"""
        file_path = params.get("path", "")
        
        logger.info(f"🔍 识别文件类型: {file_path}")
        
        try:
            # 验证文件路径
            if not file_path:
                error_msg = "❌ 文件路径不能为空"
                logger.warning(error_msg)
                return error_msg
            
            if not os.path.exists(file_path):
                error_msg = f"❌ 文件不存在: {file_path}"
                logger.warning(error_msg)
                return error_msg
            
            if os.path.isdir(file_path):
                error_msg = f"❌ 路径是目录，不是文件: {file_path}"
                logger.warning(error_msg)
                return error_msg
            
            # 根据扩展名识别
            ext_type = self._recognize_file_type_by_extension(file_path)
            # 根据内容识别
            content_type = self._recognize_file_type_by_content(file_path)
            
            # 确定最终类型
            final_type = content_type if content_type != "unknown" else ext_type
            
            result = f"📄 文件类型识别结果:\n\n"
            result += f"📁 文件路径: {file_path}\n"
            result += f"🔍 根据扩展名识别: {ext_type}\n"
            result += f"🔍 根据内容识别: {content_type}\n"
            result += f"✅ 最终识别结果: {final_type}\n"
            
            logger.info(f"🔍 文件类型识别完成: {final_type}")
            return result
        except Exception as e:
            error_msg = f"❌ 识别文件类型失败: {str(e)}"
            logger.error(f"❌ 识别文件类型失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    async def _handle_analyze_file(self, params: Dict) -> str:
        """分析文件内容"""
        file_path = params.get("path", "")
        
        logger.info(f"🔍 分析文件内容: {file_path}")
        
        try:
            # 验证文件路径
            if not file_path:
                error_msg = "❌ 文件路径不能为空"
                logger.warning(error_msg)
                return error_msg
            
            if not os.path.exists(file_path):
                error_msg = f"❌ 文件不存在: {file_path}"
                logger.warning(error_msg)
                return error_msg
            
            if os.path.isdir(file_path):
                error_msg = f"❌ 路径是目录，不是文件: {file_path}"
                logger.warning(error_msg)
                return error_msg
            
            # 获取文件基本信息
            file_size = os.path.getsize(file_path)
            file_type = self._recognize_file_type_by_extension(file_path)
            
            # 分析文件内容
            analysis_result = {
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "file_size": self._format_size(file_size),
                "file_type": file_type,
                "content_analysis": {}
            }
            
            # 根据文件类型进行不同的分析
            if file_type == "text" or file_type == "markdown":
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    words = content.split()
                    analysis_result["content_analysis"] = {
                        "line_count": len(lines),
                        "word_count": len(words),
                        "character_count": len(content),
                        "first_few_lines": lines[:5] if len(lines) > 5 else lines
                    }
                except Exception as e:
                    logger.debug(f"无法分析文本文件内容: {e}")
                    analysis_result["content_analysis"] = {"error": "无法读取文件内容"}
            
            elif file_type == "json":
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        import json
                        data = json.load(f)
                    
                    analysis_result["content_analysis"] = {
                        "type": type(data).__name__,
                        "keys": list(data.keys()) if isinstance(data, dict) else f"数组长度: {len(data)}"
                    }
                except Exception as e:
                    logger.debug(f"无法分析JSON文件内容: {e}")
                    analysis_result["content_analysis"] = {"error": "无法解析JSON文件"}
            
            elif file_type == "python":
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    import re
                    # 简单分析Python文件
                    functions = re.findall(r'def\s+(\w+)\s*\(', content)
                    classes = re.findall(r'class\s+(\w+)\s*\(', content)
                    imports = re.findall(r'import\s+(\w+)|from\s+(\w+)\s+import', content)
                    imports = [imp[0] or imp[1] for imp in imports]
                    
                    analysis_result["content_analysis"] = {
                        "function_count": len(functions),
                        "class_count": len(classes),
                        "import_count": len(imports),
                        "functions": functions[:10] if len(functions) > 10 else functions,
                        "classes": classes
                    }
                except Exception as e:
                    logger.debug(f"无法分析Python文件内容: {e}")
                    analysis_result["content_analysis"] = {"error": "无法分析Python文件"}
            
            elif file_type in ["jpg", "jpeg", "png", "gif", "bmp"]:
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        width, height = img.size
                        mode = img.mode
                        format = img.format
                    
                    analysis_result["content_analysis"] = {
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "format": format,
                        "resolution": f"{width}x{height}"
                    }
                except ImportError:
                    analysis_result["content_analysis"] = {"note": "需要PIL库来分析图像文件"}
                except Exception as e:
                    logger.debug(f"无法分析图像文件内容: {e}")
                    analysis_result["content_analysis"] = {"error": "无法分析图像文件"}
            
            elif file_type == "pdf":
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        page_count = len(reader.pages)
                    
                    analysis_result["content_analysis"] = {
                        "page_count": page_count
                    }
                except ImportError:
                    analysis_result["content_analysis"] = {"note": "需要PyPDF2库来分析PDF文件"}
                except Exception as e:
                    logger.debug(f"无法分析PDF文件内容: {e}")
                    analysis_result["content_analysis"] = {"error": "无法分析PDF文件"}
            
            else:
                analysis_result["content_analysis"] = {"note": "暂不支持此文件类型的详细分析"}
            
            # 格式化分析结果
            result = f"📄 文件分析结果:\n\n"
            result += f"📁 文件名: {analysis_result['file_name']}\n"
            result += f"📁 文件路径: {analysis_result['file_path']}\n"
            result += f"💾 文件大小: {analysis_result['file_size']}\n"
            result += f"🔍 文件类型: {analysis_result['file_type']}\n"
            result += "\n📊 内容分析:\n"
            
            for key, value in analysis_result['content_analysis'].items():
                if isinstance(value, list):
                    value_str = "\n  - " + "\n  - ".join(str(item) for item in value)
                else:
                    value_str = str(value)
                result += f"  {key}: {value_str}\n"
            
            logger.info(f"🔍 文件内容分析完成: {analysis_result['file_name']}")
            return result
        except Exception as e:
            error_msg = f"❌ 分析文件内容失败: {str(e)}"
            logger.error(f"❌ 分析文件内容失败: {e}")
            logger.exception("详细错误信息:")
            return error_msg

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size >= 1024 ** 3:
            return f"{size / (1024 ** 3):.2f} GB"
        elif size >= 1024 ** 2:
            return f"{size / (1024 ** 2):.2f} MB"
        elif size >= 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size} B"

    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = super().get_status()
        status.update({
            "operation_count": self.operation_count
        })
        return status
