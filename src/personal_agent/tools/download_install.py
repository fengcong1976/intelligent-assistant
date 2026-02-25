"""
Download and Install Tool - 下载并安装工具

组合功能：先下载安装包，然后执行安装
"""
import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger

from .base import BaseTool, ToolResult, tool_registry
from .download import DownloadTool
from .installer import InstallTool


class DownloadAndInstallTool(BaseTool):
    """下载并安装工具 - 一步完成下载和安装"""

    name = "download_and_install"
    description = "下载安装包并执行安装，支持.exe和.msi文件"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "安装包下载链接"
            },
            "filename": {
                "type": "string",
                "description": "保存的文件名（可选）"
            },
            "save_path": {
                "type": "string",
                "description": "保存路径，默认为./downloads",
                "default": "./downloads"
            },
            "silent": {
                "type": "boolean",
                "description": "是否静默安装",
                "default": True
            }
        },
        "required": ["url"]
    }

    def __init__(self):
        self.download_tool = DownloadTool()
        self.install_tool = InstallTool()

    async def execute(self, **kwargs) -> ToolResult:
        """执行下载并安装"""
        url = kwargs.get('url')
        filename = kwargs.get('filename')
        save_path = kwargs.get('save_path', './downloads')
        silent = kwargs.get('silent', True)

        if not url:
            return ToolResult(success=False, error="下载链接不能为空")

        try:
            # 步骤1: 下载文件
            logger.info(f"开始下载安装包: {url}")
            download_result = await self.download_tool.execute(
                url=url,
                save_path=save_path,
                filename=filename
            )

            if not download_result.success:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"下载失败: {download_result.error}"
                )

            # 获取下载的文件路径
            file_path = download_result.data.get('file_path')
            if not file_path:
                return ToolResult(
                    success=False,
                    output="",
                    error="下载成功但无法获取文件路径"
                )

            # 步骤2: 执行安装
            logger.info(f"开始安装: {file_path}")
            install_result = await self.install_tool.execute(
                package_name=Path(file_path).stem,
                installer_path=file_path,
                silent=silent
            )

            if install_result.success:
                return ToolResult(
                    success=True,
                    output=f"✅ 下载并安装成功！\n\n"
                           f"📥 下载信息:\n{download_result.output}\n\n"
                           f"📦 安装信息:\n{install_result.output}",
                    data={
                        'download': download_result.data,
                        'install': install_result.data
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"下载成功但安装失败: {install_result.error}",
                    data={'download': download_result.data}
                )

        except Exception as e:
            logger.error(f"下载安装错误: {e}")
            return ToolResult(success=False, output="", error=f"操作失败: {str(e)}")


def register_download_install_tools():
    """注册下载安装工具"""
    tool_registry.register(DownloadAndInstallTool())
