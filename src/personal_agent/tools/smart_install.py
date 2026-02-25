"""
Smart Install Tool - 智能安装工具

动态查询winget仓库，自动安装软件
"""
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

from loguru import logger

from .base import BaseTool, ToolResult, tool_registry
from .download import DownloadTool
from .installer import InstallTool
from .software_sources import software_source_manager, DownloadSourceType
from ..utils.progress import progress_manager


class SmartInstallTool(BaseTool):
    """智能安装工具 - 动态查询winget仓库并安装"""

    name = "smart_install"
    description = """【推荐】智能安装软件，这是最可靠的安装方式！

功能特点：
1. 【动态查询】自动从微软winget仓库查询软件，无需预定义列表
2. 【智能匹配】支持中英文软件名称，自动匹配最佳结果
3. 【多种方式】优先winget安装，失败时回退到官网下载
4. 【进度显示】实时显示下载和安装进度

使用方法：
- 直接输入软件名称，如：剪映、微信、vscode、chrome等
- 支持中英文名称，如：网易云音乐 或 netease-cloud-music
"""
    parameters = {
        "type": "object",
        "properties": {
            "software_name": {
                "type": "string",
                "description": "软件名称，如：剪映、微信、vscode、chrome等"
            },
            "method": {
                "type": "string",
                "description": "安装方式：auto(自动)/download(下载安装)/winget",
                "enum": ["auto", "download", "winget"],
                "default": "auto"
            },
            "silent": {
                "type": "boolean",
                "description": "是否静默安装",
                "default": True
            }
        },
        "required": ["software_name"]
    }

    CHINESE_TO_ENGLISH = {
        "qq音乐": "QQMusic",
        "QQ音乐": "QQMusic",
        "qqmusic": "QQMusic",
        "网易云音乐": "NeteaseCloudMusic",
        "网易音乐": "NeteaseCloudMusic",
        "酷狗音乐": "KuGou",
        "酷我音乐": "KuWo",
        "虾米音乐": "Xiami",
        "微信": "WeChat",
        "wechat": "WeChat",
        "抖音": "Douyin",
        "douyin": "Douyin",
        "快手": "Kuaishou",
        "哔哩哔哩": "Bilibili",
        "b站": "Bilibili",
        "百度网盘": "BaiduNetdisk",
        "百度云": "BaiduNetdisk",
        "阿里云盘": "AliyunDrive",
        "腾讯视频": "TencentVideo",
        "爱奇艺": "iQIYI",
        "优酷": "Youku",
        "芒果tv": "MangoTV",
        "搜狗输入法": "SogouInput",
        "百度输入法": "BaiduInput",
        "讯飞输入法": "iFlyIME",
        "wps": "WPS Office",
        "office": "Microsoft Office",
        "vscode": "Visual Studio Code",
        "visual studio code": "Visual Studio Code",
        "pycharm": "PyCharm",
        "idea": "IntelliJ IDEA",
        "sublime": "Sublime Text",
        "notepad": "Notepad++",
        "7zip": "7-Zip",
        "winrar": "WinRAR",
        "解压": "7-Zip",
        "截图": "Snipaste",
        "录屏": "OBS Studio",
        "obs": "OBS Studio",
        "直播": "OBS Studio",
        "视频剪辑": "CapCut",
        "剪映": "CapCut",
        "capcut": "CapCut",
        "photoshop": "Adobe Photoshop",
        "ps": "Adobe Photoshop",
        "ai": "Adobe Illustrator",
        "cad": "AutoCAD",
        "思维导图": "XMind",
        "xmind": "XMind",
        "笔记": "Notion",
        "notion": "Notion",
        "印象笔记": "Evernote",
        "有道云笔记": "YoudaoNote",
        "翻译": "DeepL",
        "deepl": "DeepL",
        "有道翻译": "YoudaoDict",
        "词典": "YoudaoDict",
        "有道词典": "YoudaoDict",
        "迅雷": "Xunlei",
        "下载器": "Xunlei",
        "idm": "Internet Download Manager",
        "motrix": "Motrix",
        "浏览器": "Google Chrome",
        "chrome": "Google Chrome",
        "谷歌浏览器": "Google Chrome",
        "edge": "Microsoft Edge",
        "firefox": "Mozilla Firefox",
        "火狐": "Mozilla Firefox",
        "qq浏览器": "QQBrowser",
        "360浏览器": "360Browser",
        "终端": "Windows Terminal",
        "terminal": "Windows Terminal",
        "powershell": "PowerShell",
        "git": "Git",
        "svn": "TortoiseSVN",
        "node": "Node.js",
        "nodejs": "Node.js",
        "python": "Python",
        "java": "Java",
        "jdk": "Java",
        "go": "Go",
        "golang": "Go",
        "rust": "Rust",
        "docker": "Docker Desktop",
        "redis": "Redis",
        "mysql": "MySQL",
        "数据库": "MySQL",
        "mongodb": "MongoDB",
        "postman": "Postman",
        "远程桌面": "Microsoft Remote Desktop",
        "向日葵": "Sunlogin",
        "teamviewer": "TeamViewer",
        "todesk": "ToDesk",
        "会议": "Tencent Meeting",
        "腾讯会议": "Tencent Meeting",
        "zoom": "Zoom",
        "钉钉": "DingTalk",
        "飞书": "Feishu",
        "企业微信": "WeCom",
        "音乐播放器": "QQMusic",
        "视频播放器": "PotPlayer",
        "potplayer": "PotPlayer",
        "vlc": "VLC",
        "暴风影音": "Baofeng",
        "迅雷影音": "XunleiPlayer",
    }

    def __init__(self):
        self.download_tool = DownloadTool()
        self.install_tool = InstallTool()

    def _get_search_name(self, software_name: str) -> str:
        """获取用于搜索的名称（中英文映射）"""
        name_lower = software_name.lower().strip()
        
        lower_to_english = {k.lower(): v for k, v in self.CHINESE_TO_ENGLISH.items()}
        
        if name_lower in lower_to_english:
            return lower_to_english[name_lower]
        
        for cn_name_lower, en_name in lower_to_english.items():
            if cn_name_lower in name_lower or name_lower in cn_name_lower:
                return en_name
        
        return software_name

    def _is_installed(self, package_id: str) -> bool:
        """检查软件是否已安装"""
        try:
            result = subprocess.run(
                ['winget', 'list', '--id', package_id],
                capture_output=True,
                text=True,
                timeout=15
            )
            return package_id.lower() in result.stdout.lower()
        except:
            return False

    async def _search_winget(self, software_name: str) -> List[Tuple[str, str, str]]:
        """
        使用winget search搜索软件
        
        Returns:
            List of (package_id, package_name, source) tuples
        """
        try:
            progress_manager.report(f"正在winget仓库搜索: {software_name}", -1)
            
            proc = await asyncio.create_subprocess_exec(
                'winget', 'search', software_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=30
            )
            
            output = stdout.decode('utf-8', errors='ignore')
            
            results = []
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or '---' in line or '名称' in line or 'Name' in line.lower():
                    continue
                
                import re
                id_match = re.search(r'([A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+)', line)
                if id_match:
                    package_id = id_match.group(1)
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        source = "winget"
                        for p in reversed(parts):
                            if p.lower() in ["winget", "msstore", "chocolatey"]:
                                source = p
                                break
                        
                        id_pos = line.find(package_id)
                        if id_pos > 0:
                            package_name = line[:id_pos].strip()
                        else:
                            package_name = parts[0] if parts else ""
                        
                        results.append((package_id, package_name, source))
            
            logger.info(f"winget search 找到 {len(results)} 个结果")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("winget search 超时")
            return []
        except Exception as e:
            logger.error(f"winget search 失败: {e}")
            return []

    def _select_best_match(self, software_name: str, results: List[Tuple[str, str, str]]) -> Optional[str]:
        """
        从搜索结果中选择最佳匹配
        
        优先级：
        1. ID中包含软件名称的
        2. 名称完全匹配的
        3. 第一个结果
        """
        if not results:
            return None
        
        software_lower = software_name.lower()
        
        for package_id, package_name, source in results:
            if software_lower in package_id.lower():
                return package_id
        
        for package_id, package_name, source in results:
            if software_lower == package_name.lower():
                return package_id
        
        return results[0][0]

    async def execute(self, **kwargs) -> ToolResult:
        """执行智能安装"""
        software_name = kwargs.get('software_name', '').strip()
        method = kwargs.get('method', 'auto')
        silent = kwargs.get('silent', True)

        if not software_name:
            return ToolResult(
                success=False,
                output="",
                error="请提供软件名称"
            )

        progress_manager.report(f"正在查找软件: {software_name}", -1)

        source = software_source_manager.get(software_name)
        winget_package_id = None

        if source:
            progress_manager.report(f"本地配置找到: {source.description}", -1)
            if source.source_type == DownloadSourceType.WINGET:
                winget_package_id = source.url_template
                progress_manager.report(f"使用预配置的winget ID: {winget_package_id}", -1)
        else:
            if shutil.which('winget'):
                search_name = self._get_search_name(software_name)
                if search_name != software_name:
                    progress_manager.report(f"使用英文名称搜索: {search_name}", -1)
                
                results = await self._search_winget(search_name)
                winget_package_id = self._select_best_match(search_name, results)
                
                if winget_package_id:
                    progress_manager.report(f"winget仓库找到: {winget_package_id}", -1)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"未找到软件 '{software_name}'\n\n"
                              f"建议：\n"
                              f"1. 检查软件名称是否正确\n"
                              f"2. 尝试使用英文名称搜索\n"
                              f"3. 使用 web_search 搜索官方下载地址"
                    )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"未找到软件 '{software_name}'，且系统未安装winget\n\n"
                          f"建议：使用 web_search 搜索官方下载地址"
                )

        if source:
            winget_name = getattr(source, 'winget_id', None) or source.url_template if source.source_type == DownloadSourceType.WINGET else None
            if winget_name and self._is_installed(winget_name):
                return ToolResult(
                    success=True,
                    output=f"✅ {source.description} 已经安装过了！"
                )
        elif winget_package_id and self._is_installed(winget_package_id):
            return ToolResult(
                success=True,
                output=f"✅ {software_name} 已经安装过了！"
            )

        if method == 'auto':
            if winget_package_id:
                method = 'winget'
            elif source and source.source_type != DownloadSourceType.OFFICIAL_API:
                method = 'winget'
            elif source:
                method = 'download'
            else:
                method = 'winget'

        if method == 'winget':
            if winget_package_id:
                result = await self._install_with_winget_id(winget_package_id, silent)
            elif source:
                result = await self._install_from_source_winget(source, silent)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="无法确定winget包ID"
                )
            
            if not result.success and source and source.source_type != DownloadSourceType.WINGET:
                progress_manager.report("winget安装失败，尝试下载安装...", -1)
                result = await self._install_with_download(source, silent)
            return result
        else:
            if source and source.source_type != DownloadSourceType.WINGET:
                return await self._install_with_download(source, silent)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"系统未安装winget，无法安装 {software_name}"
                )

    async def _install_with_winget_id(self, package_id: str, silent: bool) -> ToolResult:
        """使用winget ID直接安装"""
        progress_manager.report(f"使用 winget 安装: {package_id}", -1)
        progress_manager.report("⏳ 正在下载和安装，请耐心等待...", -1)

        result = await self.install_tool.execute(
            package_name=package_id,
            method="winget",
            silent=silent
        )

        return result

    async def _install_from_source_winget(self, source, silent: bool) -> ToolResult:
        """使用winget安装（本地配置的软件）"""
        progress_manager.report(f"使用 winget 安装: {source.description}", -1)
        progress_manager.report("⏳ 正在下载和安装，请耐心等待...", -1)

        results = await self._search_winget(source.name)
        package_id = self._select_best_match(source.name, results)
        
        if not package_id:
            return ToolResult(
                success=False,
                output="",
                error=f"在winget仓库中未找到 {source.description}"
            )

        result = await self.install_tool.execute(
            package_name=package_id,
            method="winget",
            silent=silent
        )

        return result

    async def _install_with_download(self, source, silent: bool) -> ToolResult:
        """下载并安装"""
        progress_manager.report(f"获取下载链接: {source.description}", -1)
        download_url = await software_source_manager.get_download_url(source.name)

        if not download_url:
            return ToolResult(
                success=False,
                output="",
                error=f"无法获取 {source.description} 的下载链接"
            )

        progress_manager.report(f"下载链接: {download_url}", -1)

        if source.filename_pattern:
            filename = f"{source.name}_setup.exe"
        else:
            filename = None

        progress_manager.report(f"开始下载: {source.description}", 0)
        download_result = await self.download_tool.execute(
            url=download_url,
            save_path="./downloads",
            filename=filename
        )

        if not download_result.success:
            if shutil.which('winget'):
                progress_manager.report(f"下载失败，尝试使用 winget 安装", -1)
                return await self._install_from_source_winget(source, silent)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"下载失败: {download_result.error}"
                )

        file_path = download_result.data.get('file_path')
        progress_manager.report(f"开始安装: {source.description}", -1)

        install_result = await self.install_tool.execute(
            package_name=source.description,
            installer_path=file_path,
            silent=silent
        )

        if install_result.success:
            return ToolResult(
                success=True,
                output=f"✅ {source.description} 安装成功！\n\n"
                       f"📥 下载信息:\n{download_result.output}\n\n"
                       f"📦 安装信息:\n{install_result.output}",
                data={
                    'software': source.name,
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


class SearchSoftwareTool(BaseTool):
    """搜索软件工具"""

    name = "search_software"
    description = """在winget仓库中搜索软件，查看是否可以安装

返回匹配的软件包列表，包括包ID和来源
"""
    parameters = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，如：剪映、微信、chrome等"
            }
        },
        "required": ["keyword"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        """执行搜索"""
        keyword = kwargs.get('keyword', '').strip()
        
        if not keyword:
            return ToolResult(
                success=False,
                output="",
                error="请提供搜索关键词"
            )

        if not shutil.which('winget'):
            return ToolResult(
                success=False,
                output="",
                error="系统未安装winget"
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                'winget', 'search', keyword,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=30
            )
            
            output = stdout.decode('utf-8', errors='ignore')
            
            results = []
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or '---' in line or '名称' in line or 'Name' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    package_id = parts[0]
                    if '.' in package_id:
                        package_name = parts[1] if len(parts) > 1 else ""
                        source = parts[-1] if len(parts) > 2 else "winget"
                        results.append({
                            "id": package_id,
                            "name": package_name,
                            "source": source
                        })
            
            if not results:
                return ToolResult(
                    success=True,
                    output=f"未找到匹配 '{keyword}' 的软件",
                    data={"results": []}
                )
            
            output_lines = [f"找到 {len(results)} 个匹配 '{keyword}' 的软件:\n"]
            for i, r in enumerate(results[:10], 1):
                output_lines.append(f"{i}. {r['name']}")
                output_lines.append(f"   ID: {r['id']}")
                output_lines.append(f"   来源: {r['source']}\n")
            
            if len(results) > 10:
                output_lines.append(f"... 还有 {len(results) - 10} 个结果")
            
            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={"results": results}
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error="搜索超时"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"搜索失败: {e}"
            )


class ListSoftwareTool(BaseTool):
    """列出支持的软件"""

    name = "list_software"
    description = "列出本地配置的支持自动下载安装的软件（非winget仓库全部软件）"
    parameters = {
        "type": "object",
        "properties": {}
    }

    async def execute(self, **kwargs) -> ToolResult:
        """执行列出软件"""
        software = software_source_manager.list_software()

        output = "本地配置的软件列表:\n\n"
        for name, desc in sorted(software.items()):
            output += f"• {desc} ({name})\n"

        output += "\n💡 提示: 使用 search_software 可以搜索winget仓库中的所有软件"

        return ToolResult(
            success=True,
            output=output,
            data={'software': software}
        )


def register_smart_install_tools():
    """注册智能安装工具"""
    tool_registry.register(SmartInstallTool())
    tool_registry.register(SearchSoftwareTool())
    tool_registry.register(ListSoftwareTool())
