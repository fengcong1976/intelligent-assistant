"""
Download Tool - 文件下载工具
"""
import asyncio
import os
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import aiohttp
from loguru import logger

from .base import BaseTool, ToolResult, tool_registry
from ..utils.progress import progress_manager


class DownloadTool(BaseTool):
    """文件下载工具"""

    name = "download_file"
    description = """从URL下载文件到本地。重要：不要编造URL！必须先使用web_search搜索获取真实的下载链接。

使用流程：
1. 使用 web_search 搜索 "软件名 官方下载" 获取真实链接
2. 使用 web_fetch 访问官网确认下载链接
3. 使用 download_file 下载文件
4. 使用 install_program 安装（如果是安装包）
"""
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要下载的文件URL（必须是真实的链接，不能编造）"
            },
            "save_path": {
                "type": "string",
                "description": "保存路径，默认为./downloads",
                "default": "./downloads"
            },
            "filename": {
                "type": "string",
                "description": "自定义文件名（可选，默认从URL提取）"
            }
        },
        "required": ["url"]
    }

    def __init__(self):
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None

    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """设置进度回调函数 (message, current, total)"""
        self.progress_callback = callback

    async def execute(self, **kwargs) -> ToolResult:
        """执行下载"""
        url = kwargs.get('url')
        save_path = kwargs.get('save_path', './downloads')
        filename = kwargs.get('filename')

        if not url:
            return ToolResult(success=False, output="", error="URL不能为空")

        # 验证URL格式
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ToolResult(
                success=False,
                output="",
                error=f"无效的URL格式: {url}\n请使用 web_search 搜索获取真实的下载链接，不要编造URL。"
            )

        # 检查是否是常见的编造域名
        suspicious_domains = ['tongyi.aliyun.com', 'example.com', 'test.com']
        if any(domain in parsed.netloc for domain in suspicious_domains):
            return ToolResult(
                success=False,
                output="",
                error=f"URL {url} 看起来不是有效的下载链接。\n请使用 web_search 搜索获取真实的下载链接，不要编造URL。"
            )

        try:
            # 创建保存目录
            save_dir = Path(save_path)
            save_dir.mkdir(parents=True, exist_ok=True)

            # 确定文件名
            if not filename:
                # 从URL提取文件名
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path)
                if not filename:
                    filename = "download_file"

            save_file = save_dir / filename

            # 通知开始下载
            progress_manager.report(f"开始下载: {filename}", 0)

            # 下载文件
            logger.info(f"开始下载: {url} -> {save_file}")

            async with aiohttp.ClientSession() as session:
                # 添加请求头，模拟浏览器
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/octet-stream,application/pdf,application/x-msdownload,*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': 'https://music.163.com/',
                }
                async with session.get(url, headers=headers, timeout=300) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"下载失败，HTTP状态码: {response.status}"
                        )

                    # 获取文件大小
                    total_size = response.headers.get('Content-Length')
                    if total_size:
                        total_size = int(total_size)

                    # 写入文件
                    downloaded = 0
                    last_progress = 0
                    with open(save_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                # 每下载10%或每1MB报告一次进度
                                if total_size:
                                    progress = int((downloaded / total_size) * 100)
                                    if progress >= last_progress + 10 or downloaded - last_progress >= 1024*1024:
                                        progress_manager.report(
                                            f"下载中: {filename}",
                                            progress
                                        )
                                        last_progress = progress

            # 获取文件大小
            file_size = save_file.stat().st_size
            size_str = self._format_size(file_size)

            # 验证文件大小 - 安装包通常至少10MB
            if file_size < 1024 * 1024:  # 小于1MB
                # 可能是HTML错误页面，尝试读取内容
                try:
                    with open(save_file, 'rb') as f:
                        header = f.read(100)
                        if b'<html' in header.lower() or b'<!doctype' in header.lower():
                            save_file.unlink()  # 删除错误文件
                            return ToolResult(
                                success=False,
                                output="",
                                error=f"下载失败：获取到的是网页而不是文件。\n"
                                      f"URL {url} 可能是一个跳转页面或需要登录。\n"
                                      f"请使用 web_fetch 工具访问该URL，从中提取真实的下载链接。"
                            )
                except:
                    pass

            # 验证文件类型 - 检查是否是可执行文件
            if filename.endswith('.exe') or filename.endswith('.msi'):
                if file_size < 10 * 1024 * 1024:  # 安装包小于10MB，可能有问题
                    logger.warning(f"警告：安装包文件过小 ({size_str})，可能不是完整的安装程序")

            # 通知下载完成
            progress_manager.report(f"下载完成: {filename}", 100)

            logger.info(f"下载完成: {save_file} ({size_str})")

            return ToolResult(
                success=True,
                output=f"✅ 下载成功！\n"
                       f"📁 文件名: {filename}\n"
                       f"📂 保存位置: {save_file.absolute()}\n"
                       f"📊 文件大小: {size_str}",
                data={
                    'file_path': str(save_file.absolute()),
                    'filename': filename,
                    'size': file_size
                }
            )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error="下载超时，请检查网络连接")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"连接错误: {e}")
            return ToolResult(success=False, output="", error=f"无法连接到服务器，请检查网络或URL是否正确: {str(e)}")
        except aiohttp.ClientError as e:
            logger.error(f"客户端错误: {e}")
            return ToolResult(success=False, output="", error=f"下载请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"下载错误: {e}")
            return ToolResult(success=False, output="", error=f"下载失败: {str(e)}")

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


def register_download_tools():
    """注册下载工具"""
    tool_registry.register(DownloadTool())
