"""
Software Download Sources - 软件下载源管理

管理常用软件的官方下载链接和获取方式
"""
import re
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

import aiohttp
from loguru import logger


class DownloadSourceType(Enum):
    """下载源类型"""
    DIRECT = "direct"           # 直接下载链接
    OFFICIAL_API = "api"        # 官方API获取
    GITHUB_RELEASE = "github"   # GitHub Release
    WINGET = "winget"           # 使用winget安装
    CHOCO = "choco"             # 使用choco安装


@dataclass
class SoftwareSource:
    """软件下载源配置"""
    name: str                           # 软件名称
    description: str                    # 软件描述
    source_type: DownloadSourceType     # 源类型
    url_template: str                   # URL模板或固定链接
    version_api: Optional[str] = None   # 版本API（用于动态获取）
    filename_pattern: Optional[str] = None  # 文件名匹配模式
    headers: Optional[Dict] = None      # 特殊请求头


class SoftwareSourceManager:
    """软件下载源管理器"""

    def __init__(self):
        self._sources: Dict[str, SoftwareSource] = {}
        self._register_default_sources()

    def _register_default_sources(self):
        """注册默认软件源"""
        # 网易云音乐
        self.register(SoftwareSource(
            name="netease-cloud-music",
            description="网易云音乐",
            source_type=DownloadSourceType.OFFICIAL_API,
            url_template="https://d1.music.126.net/dmusic/NeteaseCloudMusic_Setup.exe",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://music.163.com/'
            }
        ))

        # VS Code
        self.register(SoftwareSource(
            name="vscode",
            description="Visual Studio Code",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user",
            filename_pattern="VSCodeSetup-.*\\.exe"
        ))

        # Chrome
        self.register(SoftwareSource(
            name="chrome",
            description="Google Chrome",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://dl.google.com/chrome/install/GoogleChromeStandaloneEnterprise64.msi",
            filename_pattern="GoogleChrome.*\\.msi"
        ))

        # Firefox
        self.register(SoftwareSource(
            name="firefox",
            description="Mozilla Firefox",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://download.mozilla.org/?product=firefox-latest&os=win64&lang=zh-CN",
            filename_pattern="Firefox.*\\.exe"
        ))

        # 7-Zip
        self.register(SoftwareSource(
            name="7zip",
            description="7-Zip 压缩工具",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://www.7-zip.org/a/7z2401-x64.exe",
            filename_pattern="7z.*\\.exe"
        ))

        # Notepad++
        self.register(SoftwareSource(
            name="notepadplusplus",
            description="Notepad++ 文本编辑器",
            source_type=DownloadSourceType.GITHUB_RELEASE,
            url_template="https://github.com/notepad-plus-plus/notepad-plus-plus/releases/latest",
            filename_pattern="npp\\..*\\.Installer\\.exe"
        ))

        # Git
        self.register(SoftwareSource(
            name="git",
            description="Git 版本控制",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe",
            filename_pattern="Git-.*-64-bit\\.exe"
        ))

        # Python
        self.register(SoftwareSource(
            name="python",
            description="Python 解释器",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe",
            filename_pattern="python-.*-amd64\\.exe"
        ))

        # Node.js
        self.register(SoftwareSource(
            name="nodejs",
            description="Node.js 运行环境",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi",
            filename_pattern="node-v.*-x64\\.msi"
        ))

        # WeChat
        self.register(SoftwareSource(
            name="wechat",
            description="微信",
            source_type=DownloadSourceType.OFFICIAL_API,
            url_template="https://dldir1.qq.com/weixin/Windows/WeChatSetup.exe",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://weixin.qq.com/'
            }
        ))

        # QQ
        self.register(SoftwareSource(
            name="qq",
            description="QQ",
            source_type=DownloadSourceType.OFFICIAL_API,
            url_template="https://dldir1.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.7_240305_x64_01.exe",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://im.qq.com/'
            }
        ))

        # 钉钉 - 优先使用winget
        self.register(SoftwareSource(
            name="dingtalk",
            description="钉钉",
            source_type=DownloadSourceType.DIRECT,
            url_template="https://dtapp-pub.dingtalk.com/dingtalk-desktop/win_installer/Release/DingTalkSetup.exe",
            filename_pattern="DingTalkSetup.*\.exe",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.dingtalk.com/'
            }
        ))

        # 剪映 - 使用winget安装
        self.register(SoftwareSource(
            name="jianying",
            description="剪映",
            source_type=DownloadSourceType.WINGET,
            url_template="ByteDance.JianyingPro",
        ))

        # 抖音 - 使用winget安装
        self.register(SoftwareSource(
            name="douyin",
            description="抖音",
            source_type=DownloadSourceType.WINGET,
            url_template="ByteDance.Douyin",
        ))

    def register(self, source: SoftwareSource):
        """注册软件源"""
        self._sources[source.name.lower()] = source
        # 同时注册别名
        aliases = {
            "vscode": ["vs code", "visual studio code"],
            "netease-cloud-music": ["网易云音乐", "cloudmusic"],
            "notepadplusplus": ["notepad++", "npp"],
            "nodejs": ["node", "node.js"],
            "wechat": ["微信", "weixin"],
            "qq": ["腾讯qq"],
            "dingtalk": ["钉钉", "dingding"],
            "jianying": ["剪映", "剪映专业版", "jianyingpro"],
            "douyin": ["抖音", "douyin"],
        }
        for main_name, alias_list in aliases.items():
            if source.name.lower() == main_name:
                for alias in alias_list:
                    self._sources[alias.lower()] = source

    def get(self, name: str) -> Optional[SoftwareSource]:
        """获取软件源配置"""
        return self._sources.get(name.lower())

    def list_software(self) -> Dict[str, str]:
        """列出所有可用软件"""
        seen = set()
        result = {}
        for key, source in self._sources.items():
            if source.name not in seen:
                seen.add(source.name)
                result[source.name] = source.description
        return result

    async def get_download_url(self, name: str) -> Optional[str]:
        """获取软件下载链接"""
        source = self.get(name)
        if not source:
            return None

        if source.source_type == DownloadSourceType.DIRECT:
            return source.url_template

        elif source.source_type == DownloadSourceType.GITHUB_RELEASE:
            # 从GitHub Release获取最新版本
            return await self._get_github_release_url(source)

        elif source.source_type == DownloadSourceType.OFFICIAL_API:
            # 返回官方API链接（需要特殊处理）
            return source.url_template

        return None

    async def _get_github_release_url(self, source: SoftwareSource) -> Optional[str]:
        """从GitHub Release获取下载链接"""
        try:
            # 转换latest链接为API链接
            api_url = source.url_template.replace(
                "https://github.com/",
                "https://api.github.com/repos/"
            ).replace("/releases/latest", "/releases/latest")

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        assets = data.get("assets", [])
                        for asset in assets:
                            name = asset.get("name", "")
                            if re.match(source.filename_pattern or ".*", name):
                                return asset.get("browser_download_url")
        except Exception as e:
            logger.error(f"获取GitHub Release失败: {e}")

        return None

    def get_headers(self, name: str) -> Optional[Dict]:
        """获取软件下载需要的特殊请求头"""
        source = self.get(name)
        if source:
            return source.headers
        return None


# 全局软件源管理器
software_source_manager = SoftwareSourceManager()
