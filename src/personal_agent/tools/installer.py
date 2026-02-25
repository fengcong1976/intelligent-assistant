"""
Installer Tool - 程序安装工具

支持：
- 执行 .exe / .msi 安装包
- 使用 winget 安装 Windows 应用
- 使用 pip 安装 Python 包
"""
import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable

from loguru import logger

from .base import BaseTool, ToolResult, tool_registry
from ..utils.progress import progress_manager


class InstallTool(BaseTool):
    """程序安装工具"""

    name = "install_program"
    description = """安装应用程序。支持以下方式：
1. 本地安装包：提供installer_path参数执行.exe/.msi文件
2. winget包管理器：直接安装Windows应用（推荐，最可靠）
3. pip包管理器：安装Python包

重要：
- 优先使用 winget 方式安装（如果软件在winget仓库中）
- 如果需要用本地安装包，必须先通过download_file下载
- 不要编造installer_path！必须通过下载获取真实文件路径
"""
    parameters = {
        "type": "object",
        "properties": {
            "package_name": {
                "type": "string",
                "description": "程序名称或安装包路径"
            },
            "installer_path": {
                "type": "string",
                "description": "本地安装包路径（.exe或.msi），如果有的话"
            },
            "method": {
                "type": "string",
                "description": "安装方式: auto/winget/pip/exe",
                "enum": ["auto", "winget", "pip", "exe"],
                "default": "auto"
            },
            "silent": {
                "type": "boolean",
                "description": "是否静默安装",
                "default": True
            }
        },
        "required": ["package_name"]
    }

    def __init__(self):
        self.progress_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

    def _notify(self, message: str):
        """发送进度通知"""
        progress_manager.report(message, -1)
        logger.info(message)

    async def execute(self, **kwargs) -> ToolResult:
        """执行安装"""
        package_name = kwargs.get('package_name')
        installer_path = kwargs.get('installer_path')
        method = kwargs.get('method', 'auto')
        silent = kwargs.get('silent', True)

        if not package_name:
            return ToolResult(success=False, output="", error="程序名称不能为空")

        try:
            # 如果提供了本地安装包路径，直接执行
            if installer_path and Path(installer_path).exists():
                return await self._install_from_exe(installer_path, silent)

            # 根据方法选择安装方式
            if method == 'exe':
                return ToolResult(success=False, output="", error="使用exe方式需要提供installer_path参数")
            elif method == 'winget':
                return await self._install_with_winget(package_name, silent)
            elif method == 'pip':
                return await self._install_with_pip(package_name)
            else:  # auto
                # 自动选择安装方式
                if shutil.which('winget'):
                    return await self._install_with_winget(package_name, silent)
                elif shutil.which('pip'):
                    return await self._install_with_pip(package_name)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error="未找到可用的包管理器，请安装 winget 或 pip"
                    )

        except Exception as e:
            logger.error(f"安装错误: {e}")
            return ToolResult(success=False, output="", error=f"安装失败: {str(e)}")

    async def _install_from_exe(self, installer_path: str, silent: bool) -> ToolResult:
        """从.exe或.msi文件安装"""
        installer = Path(installer_path)

        if not installer.exists():
            return ToolResult(success=False, output="", error=f"安装包不存在: {installer_path}")

        self._notify(f"开始安装: {installer.name}")

        # 构建安装命令
        if installer.suffix.lower() == '.msi':
            # MSI 安装
            if silent:
                cmd = ['msiexec', '/i', str(installer), '/qn', '/norestart']
            else:
                cmd = ['msiexec', '/i', str(installer)]
        else:
            # EXE 安装
            installer_name_lower = installer.name.lower()
            if silent:
                # 根据不同的安装包类型使用不同的静默参数
                if 'dingtalk' in installer_name_lower or '钉钉' in installer.name:
                    # 钉钉使用Inno Setup打包，使用/VERYSILENT参数
                    cmd = [str(installer), '/VERYSILENT', '/NORESTART', '/SUPPRESSMSGBOXES']
                elif 'wechat' in installer_name_lower or '微信' in installer.name:
                    # 微信静默安装
                    cmd = [str(installer), '/S']
                else:
                    # 通用静默参数
                    cmd = [str(installer), '/S', '/silent', '/quiet']
            else:
                cmd = [str(installer)]

        # 执行安装
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            self._notify(f"安装完成: {installer.name}")
            return ToolResult(
                success=True,
                output=f"✅ 安装成功！\n"
                       f"📦 安装包: {installer.name}\n"
                       f"📂 安装路径: {installer.absolute()}",
                data={'installer': str(installer.absolute())}
            )
        else:
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知错误"
            return ToolResult(
                success=False,
                output="",
                error=f"安装失败 (返回码: {process.returncode}): {error_msg}"
            )

    async def _install_with_winget(self, package_name: str, silent: bool) -> ToolResult:
        """使用 winget 安装"""
        if not shutil.which('winget'):
            return ToolResult(success=False, output="", error="winget 未安装或不在PATH中")

        logger.info(f"使用 winget 安装: {package_name}")

        cmd = ['winget', 'install', '--accept-package-agreements', '--accept-source-agreements']

        if silent:
            cmd.append('--silent')

        cmd.extend(['-e', package_name])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        output = stdout.decode('utf-8', errors='ignore')

        success_indicators = [
            "已成功安装",
            "Successfully installed",
            "Successfully verified installer hash",
            "Starting package install"
        ]
        is_success = process.returncode == 0 and any(indicator in output for indicator in success_indicators)

        if is_success:
            return ToolResult(
                success=True,
                output=f"✅ 使用 winget 安装成功！\n📦 程序: {package_name}",
                data={'package': package_name, 'manager': 'winget'}
            )
        else:
            error_msg = stderr.decode('utf-8', errors='ignore')
            return ToolResult(
                success=False,
                output="",
                error=f"winget 安装失败: {error_msg or '安装程序可能需要用户交互'}",
                data={'output': output}
            )

    async def _install_with_pip(self, package_name: str) -> ToolResult:
        """使用 pip 安装"""
        pip_cmd = shutil.which('pip') or shutil.which('pip3')
        if not pip_cmd:
            return ToolResult(success=False, output="", error="pip 未安装或不在PATH中")

        logger.info(f"使用 pip 安装: {package_name}")

        cmd = [pip_cmd, 'install', package_name]

        process = await asyncio.subprocess.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        output = stdout.decode('utf-8', errors='ignore')

        if process.returncode == 0 and ("Successfully installed" in output or "Requirement already satisfied" in output):
            return ToolResult(
                success=True,
                output=f"✅ 使用 pip 安装成功！\n"
                       f"📦 包名: {package_name}\n"
                       f"📋 输出:\n{output}",
                data={'package': package_name, 'manager': 'pip'}
            )
        else:
            error_msg = stderr.decode('utf-8', errors='ignore')
            return ToolResult(
                success=False,
                error=f"pip 安装失败: {error_msg}",
                data={'output': output}
            )


class UninstallTool(BaseTool):
    """程序卸载工具"""

    name = "uninstall_program"
    description = "卸载已安装的程序"
    parameters = {
        "type": "object",
        "properties": {
            "package_name": {
                "type": "string",
                "description": "程序包名称"
            },
            "method": {
                "type": "string",
                "description": "卸载方式: winget/pip",
                "enum": ["winget", "pip"],
                "default": "winget"
            }
        },
        "required": ["package_name"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        """执行卸载"""
        package_name = kwargs.get('package_name')
        method = kwargs.get('method', 'winget')

        if not package_name:
            return ToolResult(success=False, output="", error="程序名称不能为空")

        try:
            if method == 'winget':
                return await self._uninstall_with_winget(package_name)
            elif method == 'pip':
                return await self._uninstall_with_pip(package_name)
            else:
                return ToolResult(success=False, output="", error=f"不支持的卸载方式: {method}")

        except Exception as e:
            logger.error(f"卸载错误: {e}")
            return ToolResult(success=False, output="", error=f"卸载失败: {str(e)}")

    async def _uninstall_with_winget(self, package_name: str) -> ToolResult:
        """使用 winget 卸载"""
        if not shutil.which('winget'):
            return ToolResult(success=False, output="", error="winget 未安装")

        cmd = ['winget', 'uninstall', '-e', package_name]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return ToolResult(
                success=True,
                output=f"✅ 已卸载: {package_name}"
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=stderr.decode('utf-8', errors='ignore')
            )

    async def _uninstall_with_pip(self, package_name: str) -> ToolResult:
        """使用 pip 卸载"""
        pip_cmd = shutil.which('pip') or shutil.which('pip3')
        if not pip_cmd:
            return ToolResult(success=False, output="", error="pip 未安装")

        cmd = [pip_cmd, 'uninstall', '-y', package_name]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return ToolResult(
                success=True,
                output=f"✅ 已卸载: {package_name}"
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=stderr.decode('utf-8', errors='ignore')
            )


def register_installer_tools():
    """注册安装工具"""
    tool_registry.register(InstallTool())
    tool_registry.register(UninstallTool())
