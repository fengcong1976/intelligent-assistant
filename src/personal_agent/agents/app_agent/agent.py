"""
应用智能体 - 控制第三方应用程序的打开、关闭，以及带参数打开文件
"""
import asyncio
import subprocess
import platform
import os
import shutil
import winreg
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger

from ..base import BaseAgent, Task


class AppAgent(BaseAgent):
    """应用智能体 - 控制第三方应用程序，支持打开、关闭、安装应用"""
    
    KEYWORD_MAPPINGS = {
        "打开": ("open", {}),
        "关闭": ("close", {}),
        "启动应用": ("open", {}),
        "关闭应用": ("close", {}),
        "运行程序": ("open", {}),
        "打开应用": ("open", {}),
        "关闭程序": ("close", {}),
        "退出应用": ("close", {}),
        "安装": ("install", {}),
        "安装应用": ("install", {}),
        "安装软件": ("install", {}),
        "下载应用": ("install", {}),
        "查看启动项": ("list_startup_items", {}),
        "启动项": ("list_startup_items", {}),
        "开机启动项": ("list_startup_items", {}),
        "查看开机启动": ("list_startup_items", {}),
        "禁用启动项": ("disable_startup", {}),
        "关闭启动项": ("disable_startup", {}),
        "禁止开机启动": ("disable_startup", {}),
        "禁用开机启动": ("disable_startup", {}),
        "启用启动项": ("enable_startup", {}),
        "开启启动项": ("enable_startup", {}),
        "允许开机启动": ("enable_startup", {}),
        "启用开机启动": ("enable_startup", {}),
    }

    def __init__(self):
        super().__init__(
            name="app_agent",
            description="应用智能体 - 控制第三方应用程序的打开、关闭，以及带参数打开文件"
        )
        
        self.register_capability(
            capability="open_app",
            description="打开电脑上的应用程序。可以打开已安装的软件。",
            aliases=[
                "打开应用", "打开软件", "打开程序", "启动应用", "启动软件", "启动程序",
                "打开QQ", "打开微信", "打开浏览器", "打开Chrome", "打开Edge",
                "打开VS Code", "打开记事本", "打开计算器", "打开画图",
                "打开QQ音乐", "打开网易云音乐", "打开酷狗音乐", "打开暴风影音",
                "打开WPS", "打开Office", "打开Photoshop", "打开记事本++",
                "打开edge浏览器", "打开chrome浏览器", "打开qq浏览器", "打开firefox浏览器",
                "打开360浏览器", "打开搜狗浏览器", "打开猎豹浏览器", "打开傲游浏览器",
                "打开抖音", "打开Douyin", "打开TikTok"
            ],
            alias_params={
                "打开QQ": {"app_name": "QQ"},
                "打开微信": {"app_name": "微信"},
                "打开浏览器": {"app_name": "浏览器"},
                "打开Chrome": {"app_name": "Chrome"},
                "打开Edge": {"app_name": "Edge"},
                "打开VS Code": {"app_name": "VS Code"},
                "打开QQ音乐": {"app_name": "QQ音乐"},
                "打开网易云音乐": {"app_name": "网易云音乐"},
                "打开酷狗音乐": {"app_name": "酷狗音乐"},
                "打开暴风影音": {"app_name": "暴风影音"},
                "打开WPS": {"app_name": "WPS"},
                "打开Office": {"app_name": "Office"},
                "打开Photoshop": {"app_name": "Photoshop"},
                "打开记事本++": {"app_name": "记事本++"},
                "打开edge浏览器": {"app_name": "Edge"},
                "打开chrome浏览器": {"app_name": "Chrome"},
                "打开qq浏览器": {"app_name": "QQ浏览器"},
                "打开firefox浏览器": {"app_name": "Firefox"},
                "打开360浏览器": {"app_name": "360浏览器"},
                "打开搜狗浏览器": {"app_name": "搜狗浏览器"},
                "打开猎豹浏览器": {"app_name": "猎豹浏览器"},
                "打开傲游浏览器": {"app_name": "傲游浏览器"},
                "打开抖音": {"app_name": "抖音"},
                "打开Douyin": {"app_name": "抖音"},
                "打开TikTok": {"app_name": "抖音"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "应用程序名称，如'微信'、'Chrome'、'VS Code'"
                    }
                },
                "required": ["app_name"]
            },
            category="app"
        )

        # 注册关闭应用的能力
        self.register_capability(
            capability="close_app",
            description="关闭电脑上正在运行的应用程序。可以关闭已打开的软件。",
            aliases=[
                "关闭应用", "关闭软件", "关闭程序", "退出应用", "退出软件", "退出程序",
                "关闭QQ", "关闭微信", "关闭浏览器", "关闭Chrome", "关闭Edge",
                "关闭VS Code", "关闭记事本", "关闭计算器", "关闭画图",
                "关闭QQ音乐", "关闭网易云音乐", "关闭酷狗音乐", "关闭暴风影音",
                "关闭WPS", "关闭Office", "关闭Photoshop", "关闭记事本++",
                "关闭edge浏览器", "关闭chrome浏览器", "关闭qq浏览器", "关闭firefox浏览器",
                "关闭360浏览器", "关闭搜狗浏览器", "关闭猎豹浏览器", "关闭傲游浏览器",
                "关闭抖音", "关闭Douyin", "关闭TikTok", "关闭腾讯元宝", "关闭元宝"
            ],
            alias_params={
                "关闭QQ": {"app_name": "QQ"},
                "关闭微信": {"app_name": "微信"},
                "关闭浏览器": {"app_name": "浏览器"},
                "关闭Chrome": {"app_name": "Chrome"},
                "关闭Edge": {"app_name": "Edge"},
                "关闭VS Code": {"app_name": "VS Code"},
                "关闭QQ音乐": {"app_name": "QQ音乐"},
                "关闭网易云音乐": {"app_name": "网易云音乐"},
                "关闭酷狗音乐": {"app_name": "酷狗音乐"},
                "关闭暴风影音": {"app_name": "暴风影音"},
                "关闭WPS": {"app_name": "WPS"},
                "关闭Office": {"app_name": "Office"},
                "关闭Photoshop": {"app_name": "Photoshop"},
                "关闭记事本++": {"app_name": "记事本++"},
                "关闭edge浏览器": {"app_name": "Edge"},
                "关闭chrome浏览器": {"app_name": "Chrome"},
                "关闭qq浏览器": {"app_name": "QQ浏览器"},
                "关闭firefox浏览器": {"app_name": "Firefox"},
                "关闭360浏览器": {"app_name": "360浏览器"},
                "关闭搜狗浏览器": {"app_name": "搜狗浏览器"},
                "关闭猎豹浏览器": {"app_name": "猎豹浏览器"},
                "关闭傲游浏览器": {"app_name": "傲游浏览器"},
                "关闭抖音": {"app_name": "抖音"},
                "关闭Douyin": {"app_name": "抖音"},
                "关闭TikTok": {"app_name": "抖音"},
                "关闭腾讯元宝": {"app_name": "腾讯元宝"},
                "关闭元宝": {"app_name": "腾讯元宝"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "应用程序名称，如'微信'、'Chrome'、'腾讯元宝'"
                    }
                },
                "required": ["app_name"]
            },
            category="app"
        )
        
        self.register_capability(
            capability="install_app",
            description="安装电脑上的应用程序。可以安装各种软件。",
            aliases=[
                "安装", "安装应用", "安装软件", "下载应用", "安装程序",
                "安装QQ", "安装微信", "安装Chrome", "安装Edge", "安装VS Code",
                "安装网易云音乐", "安装QQ音乐", "安装酷狗音乐", "安装暴风影音",
                "安装WPS", "安装Office", "安装Photoshop", "安装记事本++",
                "安装抖音", "安装Douyin", "安装TikTok"
            ],
            alias_params={
                "安装QQ": {"app_name": "QQ"},
                "安装微信": {"app_name": "微信"},
                "安装Chrome": {"app_name": "Chrome"},
                "安装Edge": {"app_name": "Edge"},
                "安装VS Code": {"app_name": "VS Code"},
                "安装网易云音乐": {"app_name": "网易云音乐"},
                "安装QQ音乐": {"app_name": "QQ音乐"},
                "安装酷狗音乐": {"app_name": "酷狗音乐"},
                "安装暴风影音": {"app_name": "暴风影音"},
                "安装WPS": {"app_name": "WPS"},
                "安装Office": {"app_name": "Office"},
                "安装Photoshop": {"app_name": "Photoshop"},
                "安装记事本++": {"app_name": "记事本++"},
                "安装抖音": {"app_name": "抖音"},
                "安装Douyin": {"app_name": "抖音"},
                "安装TikTok": {"app_name": "抖音"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "应用程序名称，如'QQ'、'微信'、'Chrome'"
                    }
                },
                "required": ["app_name"]
            },
            category="app"
        )

        # 注册查看运行中应用的能力
        self.register_capability(
            capability="query_running_apps",
            description="查看当前正在运行的应用程序列表。可以列出所有正在运行的进程和应用程序。",
            aliases=[
                "查看运行中的应用", "运行中的应用", "正在运行的程序",
                "查看进程", "列出运行中的应用", "显示运行中的应用"
            ],
            parameters={
                "type": "object",
                "properties": {}
            },
            category="app"
        )

        # 注册查看已安装应用的能力
        self.register_capability(
            capability="list_installed_apps",
            description="查看电脑上已安装的应用程序列表。可以列出系统中已安装的软件。",
            aliases=[
                "查看已安装应用", "已安装应用", "安装的应用",
                "查看软件列表", "列出已安装软件"
            ],
            parameters={
                "type": "object",
                "properties": {}
            },
            category="app"
        )

        # 注册查看启动项的能力
        self.register_capability(
            capability="list_startup_items",
            description="查看系统开机启动项列表。可以查看哪些程序会随系统启动而自动运行。",
            aliases=[
                "查看启动项", "启动项", "开机启动项", "查看开机启动",
                "查看启动程序", "列出启动项", "显示启动项",
                "开机自启动", "启动管理", "查看自启动"
            ],
            parameters={
                "type": "object",
                "properties": {}
            },
            category="app"
        )

        # 注册禁用启动项的能力
        self.register_capability(
            capability="disable_startup",
            description="禁用系统开机启动项。可以禁止某个程序随系统启动而自动运行。",
            aliases=[
                "禁用启动项", "关闭启动项", "禁止开机启动", "禁用开机启动",
                "关闭开机启动", "禁止自启动", "禁用自启动", "关闭自启动",
                "禁用微信启动", "禁用QQ启动", "禁用钉钉启动", "禁用腾讯元宝启动"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "要禁用的启动项名称，如'微信'、'QQ'、'钉钉'、'腾讯元宝'"
                    }
                },
                "required": ["app_name"]
            },
            category="app"
        )

        # 注册启用启动项的能力
        self.register_capability(
            capability="enable_startup",
            description="启用系统开机启动项。可以允许某个程序随系统启动而自动运行。",
            aliases=[
                "启用启动项", "开启启动项", "允许开机启动", "启用开机启动",
                "开启开机启动", "允许自启动", "启用自启动", "开启自启动",
                "启用微信启动", "启用QQ启动", "启用钉钉启动", "启用腾讯元宝启动"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "要启用的启动项名称，如'微信'、'QQ'、'钉钉'、'腾讯元宝'"
                    }
                },
                "required": ["app_name"]
            },
            category="app"
        )

        self.system = platform.system()
        self._running_processes: Dict[str, subprocess.Popen] = {}
        self._installed_apps: Dict[str, str] = {}
        self._scanned = False
        self._initializing = False
        logger.info(f"📱 应用智能体已初始化 (系统: {self.system})")

    async def async_init(self):
        """异步初始化，预加载应用信息"""
        if self._scanned or self._initializing:
            return
        
        self._initializing = True
        try:
            logger.info("🔍 预加载系统已安装的软件...")
            await self._scan_installed_apps()
            logger.info("✅ 应用信息预加载完成")
        finally:
            self._initializing = False

    async def _scan_installed_apps(self):
        """扫描系统已安装的软件"""
        if self._scanned:
            return
        
        logger.info("🔍 正在扫描系统已安装的软件...")
        
        if self.system == "Windows":
            await self._scan_windows_apps()
        
        self._scanned = True
        logger.info(f"✅ 扫描完成，发现 {len(self._installed_apps)} 个应用")

    async def _scan_windows_apps(self):
        """扫描 Windows 系统已安装的应用"""
        # 1. 扫描开始菜单
        await self._scan_start_menu()
        
        # 2. 扫描注册表
        await self._scan_registry()
        
        # 3. 扫描常见安装目录
        await self._scan_common_directories()
        
        # 4. 扫描 PATH 环境变量中的可执行文件
        await self._scan_path_executables()

    async def _scan_start_menu(self):
        """扫描开始菜单中的快捷方式"""
        try:
            import glob
            
            start_menu_paths = [
                os.path.expandvars(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"),
                os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            ]
            
            for start_menu in start_menu_paths:
                if os.path.exists(start_menu):
                    for lnk_file in glob.glob(os.path.join(start_menu, "**", "*.lnk"), recursive=True):
                        try:
                            app_name = os.path.splitext(os.path.basename(lnk_file))[0]
                            # 获取快捷方式指向的目标
                            target = self._get_shortcut_target(lnk_file)
                            if target and os.path.exists(target) and target.endswith('.exe'):
                                self._add_app_to_cache(app_name, target)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"扫描开始菜单失败: {e}")

    def _get_shortcut_target(self, lnk_path: str) -> Optional[str]:
        """获取 Windows 快捷方式指向的目标"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(lnk_path)
            return shortcut.TargetPath
        except Exception:
            return None

    async def _scan_registry(self):
        """扫描注册表获取已安装软件"""
        try:
            # 扫描卸载信息
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            
            for hkey, path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                        install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                        
                                        if install_location and os.path.exists(install_location):
                                            # 尝试在安装目录中找到可执行文件
                                            exe_path = self._find_exe_in_directory(install_location, display_name)
                                            if exe_path:
                                                self._add_app_to_cache(display_name, exe_path)
                                    except (OSError, WindowsError):
                                        pass
                            except (OSError, WindowsError):
                                pass
                except (OSError, WindowsError):
                    pass
        except Exception as e:
            logger.warning(f"扫描注册表失败: {e}")

    def _find_exe_in_directory(self, directory: str, app_name: str) -> Optional[str]:
        """在目录中查找可执行文件"""
        try:
            import glob
            exe_files = glob.glob(os.path.join(directory, "*.exe"))
            
            app_name_lower = app_name.lower().replace(" ", "").replace("-", "").replace("_", "")
            import re
            app_name_alpha = re.sub(r'[^a-z0-9]', '', app_name_lower)
            
            for exe in exe_files:
                exe_name = os.path.splitext(os.path.basename(exe))[0].lower()
                exe_name_alpha = re.sub(r'[^a-z0-9]', '', exe_name)
                
                if app_name_alpha and exe_name_alpha:
                    if app_name_alpha in exe_name_alpha or exe_name_alpha in app_name_alpha:
                        return exe
                
                if app_name_lower in exe_name or exe_name in app_name_lower:
                    return exe
            
            for exe in exe_files:
                exe_lower = os.path.basename(exe).lower()
                if "uninstall" not in exe_lower and "setup" not in exe_lower and "unins" not in exe_lower:
                    return exe
                    
        except Exception:
            pass
        return None

    async def _scan_common_directories(self):
        """扫描常见安装目录"""
        common_dirs = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local"),
            os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming"),
        ]
        
        for directory in common_dirs:
            if os.path.exists(directory):
                try:
                    for item in os.listdir(directory):
                        item_path = os.path.join(directory, item)
                        if os.path.isdir(item_path):
                            # 检查目录中是否有可执行文件
                            exe_path = self._find_exe_in_directory(item_path, item)
                            if exe_path:
                                self._add_app_to_cache(item, exe_path)
                except Exception:
                    pass

    async def _scan_path_executables(self):
        """扫描 PATH 环境变量中的可执行文件"""
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        
        for directory in path_dirs:
            if os.path.exists(directory):
                try:
                    import glob
                    for exe in glob.glob(os.path.join(directory, "*.exe")):
                        app_name = os.path.splitext(os.path.basename(exe))[0]
                        self._add_app_to_cache(app_name, exe)
                except Exception:
                    pass

    def _add_app_to_cache(self, name: str, path: str):
        """添加应用到缓存，支持多个名称映射"""
        if not name or not path or not os.path.exists(path):
            return
        
        clean_name = name.strip()
        
        self._installed_apps[clean_name.lower()] = path
        
        import re
        name_without_version = re.sub(r'\s+\d+\.\d+.*$', '', clean_name).strip()
        if name_without_version and name_without_version != clean_name:
            self._installed_apps[name_without_version.lower()] = path
        
        simple_name = re.sub(r'[^\w\u4e00-\u9fff]', '', clean_name).lower()
        if simple_name and simple_name != clean_name.lower():
            self._installed_apps[simple_name] = path
        
        # 为常见应用添加英文别名
        COMMON_APP_ALIASES = {
            "edge": ["Microsoft Edge", "msedge", "edge"],
            "chrome": ["Google Chrome", "chrome", "googlechrome"],
            "firefox": ["Mozilla Firefox", "firefox"],
            "qq": ["QQ", "qq"],
            "微信": ["WeChat", "wechat"],
            "vs code": ["Visual Studio Code", "code", "vscode"],
            "网易云音乐": ["NeteaseCloudMusic", "cloudmusic"],
            "qq音乐": ["QQMusic", "qqmusic"],
            "酷狗音乐": ["KuGou", "kugou"],
            "抖音": ["Douyin", "douyin"],
            "腾讯元宝": ["腾讯元宝", "Tencent Yuanbao", "yuanbao", "Yuanbao"],
        }
        
        # 反向映射：从中文名找到英文名
        for canonical_name, aliases in COMMON_APP_ALIASES.items():
            if clean_name in aliases:
                # 添加所有英文名作为别名
                for alias in aliases:
                    alias_lower = alias.lower()
                    if alias_lower != clean_name.lower():
                        self._installed_apps[alias_lower] = path

    async def _find_app_path(self, app_name: str) -> Optional[str]:
        """查找应用程序路径"""
        import re
        
        COMMON_APP_ALIASES = {
            "edge": ["Microsoft Edge", "msedge", "edge"],
            "chrome": ["Google Chrome", "chrome", "googlechrome"],
            "firefox": ["Mozilla Firefox", "firefox"],
            "qq": ["QQ", "qq"],
            "微信": ["WeChat", "wechat"],
            "vs code": ["Visual Studio Code", "code", "vscode"],
            "网易云音乐": ["NeteaseCloudMusic", "cloudmusic"],
            "qq音乐": ["QQMusic", "qqmusic"],
            "酷狗音乐": ["KuGou", "kugou"],
            "抖音": ["Douyin", "douyin"],
        }
        
        app_name_normalized = re.sub(r'\s+', '', app_name).strip()
        app_name_lower = app_name_normalized.lower()
        app_name_simple = re.sub(r'[^\w\u4e00-\u9fff]', '', app_name).lower()
        
        logger.info(f"📱 查找应用: '{app_name}' -> normalized='{app_name_normalized}', simple='{app_name_simple}'")
        logger.debug(f"📱 已安装应用数量: {len(self._installed_apps)}")
        
        if app_name_lower in ["浏览器", "browser"]:
            browser_priority = ["chrome", "msedge", "firefox"]
            for browser in browser_priority:
                browser_path = shutil.which(browser)
                if browser_path:
                    logger.info(f"📱 找到浏览器: {browser}")
                    return browser_path
            for name, path in self._installed_apps.items():
                name_lower = name.lower()
                if any(browser in name_lower for browser in ["chrome", "edge", "firefox", "browser"]):
                    logger.info(f"📱 从已安装应用找到浏览器: {name}")
                    return path
            logger.info(f"📱 使用系统默认浏览器")
            return "default_browser"
        
        for canonical_name, aliases in COMMON_APP_ALIASES.items():
            if app_name_lower in [alias.lower() for alias in aliases] or app_name_simple in [re.sub(r'[^\w\u4e00-\u9fff]', '', alias).lower() for alias in aliases]:
                for alias in aliases:
                    alias_lower = alias.lower()
                    if alias_lower in self._installed_apps:
                        logger.info(f"📱 通过别名映射找到应用: {app_name} -> {alias}")
                        return self._installed_apps[alias_lower]
        
        if app_name_lower in self._installed_apps:
            logger.info(f"📱 直接匹配找到应用: {app_name}")
            return self._installed_apps[app_name_lower]
        
        if app_name_simple in self._installed_apps:
            logger.info(f"📱 简化名称匹配找到应用: {app_name_simple}")
            return self._installed_apps[app_name_simple]
        
        app_name_original_lower = app_name.lower().strip()
        if app_name_original_lower in self._installed_apps:
            logger.info(f"📱 原始名称匹配找到应用: {app_name}")
            return self._installed_apps[app_name_original_lower]
        
        if shutil.which(app_name):
            logger.info(f"📱 通过 PATH 找到应用: {app_name}")
            return app_name
        
        if self.system == "Windows":
            if shutil.which(app_name + ".exe"):
                logger.info(f"📱 通过 PATH 找到应用: {app_name}.exe")
                return app_name + ".exe"
        
        fuzzy_match = self._fuzzy_match_app(app_name_lower)
        if fuzzy_match:
            logger.info(f"📱 模糊匹配找到应用: {app_name}")
            return fuzzy_match
        
        logger.info(f"📱 未找到应用 {app_name}，重新扫描系统...")
        self._scanned = False
        await self._scan_installed_apps()
        
        for canonical_name, aliases in COMMON_APP_ALIASES.items():
            if app_name_lower in [alias.lower() for alias in aliases]:
                for alias in aliases:
                    alias_lower = alias.lower()
                    if alias_lower in self._installed_apps:
                        logger.info(f"📱 重新扫描后通过别名映射找到应用: {app_name} -> {alias}")
                        return self._installed_apps[alias_lower]
        
        if app_name_lower in self._installed_apps:
            return self._installed_apps[app_name_lower]
        
        fuzzy_match = self._fuzzy_match_app(app_name_lower)
        if fuzzy_match:
            logger.info(f"📱 重新扫描后模糊匹配找到应用: {app_name}")
            return fuzzy_match
        
        logger.warning(f"📱 未找到应用: {app_name}")
        return None

    def _fuzzy_match_app(self, app_name: str) -> Optional[str]:
        """模糊匹配应用名称"""
        import re
        
        search_term = re.sub(r'[^\w\u4e00-\u9fff]', '', app_name).lower()
        
        if len(search_term) < 2:
            return None
        
        exact_matches = []
        prefix_matches = []
        suffix_matches = []
        contains_matches = []
        
        for cached_name, path in self._installed_apps.items():
            cached_simple = re.sub(r'[^\w\u4e00-\u9fff]', '', cached_name).lower()
            
            if search_term == cached_simple:
                exact_matches.append((cached_name, path))
                continue
            
            if cached_simple.startswith(search_term):
                prefix_matches.append((cached_name, path, len(cached_simple)))
                continue
            
            if search_term.startswith(cached_simple) and len(cached_simple) >= 3:
                suffix_matches.append((cached_name, path, len(cached_simple)))
                continue
            
            if search_term in cached_simple:
                contains_matches.append((cached_name, path, len(cached_simple)))
                continue
            
            if cached_simple in search_term and len(cached_simple) >= 3:
                contains_matches.append((cached_name, path, len(cached_simple)))
                continue
        
        if exact_matches:
            return exact_matches[0][1]
        
        if prefix_matches:
            prefix_matches.sort(key=lambda x: x[2])
            return prefix_matches[0][1]
        
        if suffix_matches:
            suffix_matches.sort(key=lambda x: x[2], reverse=True)
            return suffix_matches[0][1]
        
        if contains_matches:
            contains_matches.sort(key=lambda x: x[2])
            return contains_matches[0][1]
        
        return None

    async def execute_task(self, task: Task) -> str:
        """执行任务"""
        # 确保应用信息已预加载
        await self.async_init()
        
        action = task.type.lower() if task.type else ""
        if not action:
            action = task.params.get("action", "").lower()
        
        if action == "open_app":
            action = "open"
        
        operation = task.params.get("operation", "").lower()
        params = task.params
        
        if action == "app_management" and operation:
            action = operation

        logger.info(f"📱 App Agent 执行: {action}")

        try:
            if action == "open":
                return await self._open_application(
                    app_name=params.get("app_name"),
                    file_path=params.get("file_path"),
                    args=params.get("args", [])
                )
            elif action == "close" or action == "close_app":
                return await self._close_application(
                    app_name=params.get("app_name"),
                    process_name=params.get("process_name")
                )
            elif action in ["install", "install_app", "smart_install"]:
                return await self._install_app(
                    params.get("app_name") or params.get("name") or params.get("software_name")
                )
            elif action == "open_default":
                return await self._open_with_default(params.get("file_path"))
            elif action == "list_installed" or action == "list_installed_apps":
                return await self._list_installed_apps()
            elif action == "list_running" or action == "query_running_apps":
                return await self._list_running_apps()
            elif action == "list_startup" or action == "list_startup_items":
                return await self._list_startup_items()
            elif action == "disable_startup":
                return await self._disable_startup_item(params.get("app_name"))
            elif action == "enable_startup":
                return await self._enable_startup_item(params.get("app_name"))
            elif action == "is_running":
                return await self._is_running(params.get("app_name"))
            elif action == "agent_help":
                return self._get_help_info()
            else:
                return f"❌ 未知的操作: {action}"

        except Exception as e:
            logger.error(f"App Agent 执行失败: {e}")
            return f"❌ 操作失败: {str(e)}"

    async def _open_application(self, app_name: Optional[str], file_path: Optional[str], args: List[str]) -> str:
        """打开应用程序，可选带文件和参数"""
        
        if file_path and not app_name:
            return await self._open_with_default(file_path)
        
        if not app_name:
            return "❌ 请提供应用名称或文件路径"
        
        app_path = await self._find_app_path(app_name)
        if not app_path:
            logger.info(f"📱 未找到应用 {app_name}，尝试自动安装...")
            install_result = await self._install_app(app_name)
            if install_result.startswith("✅"):
                import asyncio
                await asyncio.sleep(2)
                
                self._scanned = False
                await self._scan_installed_apps()
                app_path = await self._find_app_path(app_name)
                if not app_path:
                    return f"✅ {app_name} 安装成功！\n\n请稍后在开始菜单中查找并启动，或再次对我说「打开{app_name}」"
            else:
                return install_result
        
        cmd = [app_path]
        
        if file_path:
            if os.path.exists(file_path):
                cmd.append(file_path)
            else:
                return f"❌ 文件不存在: {file_path}"
        
        if args:
            cmd.extend(args)
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
            
            self._running_processes[app_name.lower()] = process
            
            logger.info(f"📱 已启动应用: {app_name} (PID: {process.pid})")
            
            if file_path:
                return f"✅ 已用 {app_name} 打开: {Path(file_path).name}"
            else:
                return f"✅ 已启动应用: {app_name}"
                
        except Exception as e:
            logger.error(f"启动应用失败: {e}")
            return f"❌ 启动应用失败: {str(e)}"

    async def _install_app(self, app_name: str) -> str:
        """安装应用"""
        try:
            from ...tools.smart_install import SmartInstallTool
            tool = SmartInstallTool()
            result = await tool.execute(software_name=app_name)
            
            if result.success:
                self._scanned = False
                logger.info(f"📱 应用 {app_name} 安装成功，重新扫描...")
                return f"✅ {result.output}"
            else:
                return f"❌ 安装失败: {result.error}"
                
        except Exception as e:
            logger.error(f"安装应用失败: {e}")
            return f"❌ 安装失败: {str(e)}"

    async def _open_with_default(self, file_path: Optional[str]) -> str:
        """使用系统默认方式打开文件"""
        if not file_path:
            return "❌ 请提供文件路径"
        
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        try:
            abs_path = os.path.abspath(file_path)
            
            if self.system == "Windows":
                # Windows: 使用 start 命令
                os.startfile(abs_path)
            elif self.system == "Darwin":
                # macOS: 使用 open 命令
                subprocess.Popen(["open", abs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Linux: 使用 xdg-open
                subprocess.Popen(["xdg-open", abs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"📱 已用默认应用打开: {abs_path}")
            return f"✅ 已打开: {Path(file_path).name}"
            
        except Exception as e:
            logger.error(f"打开文件失败: {e}")
            return f"❌ 打开文件失败: {str(e)}"

    async def _close_application(self, app_name: Optional[str], process_name: Optional[str]) -> str:
        """关闭应用程序"""
        target = app_name or process_name
        if not target:
            return "❌ 请提供应用名称或进程名"
        
        try:
            if self.system == "Windows":
                # 首先尝试查找实际运行的进程名
                process_names = await self._find_running_process_names(target)
                
                if process_names:
                    closed_apps = []
                    for proc_name in process_names:
                        result = subprocess.run(
                            ["taskkill", "/F", "/IM", proc_name],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            closed_apps.append(proc_name.replace('.exe', ''))
                    
                    if closed_apps:
                        logger.info(f"📱 已关闭应用: {', '.join(closed_apps)}")
                        return f"✅ 已关闭: {', '.join(closed_apps)}"
                
                # 尝试直接关闭（如果进程名就是 target）
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", f"{target}.exe"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"📱 已关闭应用: {target}")
                    return f"✅ 已关闭: {target}"
                
                # 尝试关闭我们启动的进程
                target_lower = target.lower()
                if target_lower in self._running_processes:
                    process = self._running_processes[target_lower]
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    del self._running_processes[target_lower]
                    return f"✅ 已关闭: {target}"
                
                return f"⚠️ 未找到运行中的应用: {target}"
            else:
                # Linux/macOS: 使用 pkill
                result = subprocess.run(
                    ["pkill", "-f", target],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return f"✅ 已关闭: {target}"
                else:
                    return f"⚠️ 未找到运行中的应用: {target}"
                    
        except Exception as e:
            logger.error(f"关闭应用失败: {e}")
            return f"❌ 关闭应用失败: {str(e)}"

    async def _find_running_process_names(self, app_name: str) -> List[str]:
        """查找应用对应的实际运行进程名"""
        try:
            # 应用名到进程名的映射
            APP_PROCESS_MAPPING = {
                "腾讯元宝": ["yuanbao.exe", "Tencent Yuanbao.exe"],
                "元宝": ["yuanbao.exe"],
                "微信": ["WeChat.exe", "weixin.exe"],
                "qq": ["QQ.exe", "qq.exe"],
                "chrome": ["chrome.exe"],
                "edge": ["msedge.exe"],
                "firefox": ["firefox.exe"],
                "vs code": ["Code.exe"],
                "trae": ["Trae.exe", "Trae CN.exe"],
                "网易云音乐": ["cloudmusic.exe", "NeteaseCloudMusic.exe"],
                "qq音乐": ["QQMusic.exe", "qqmusic.exe"],
                "酷狗音乐": ["KuGou.exe", "kugou.exe"],
                "抖音": ["Douyin.exe", "douyin.exe"],
            }
            
            # 获取当前运行的进程列表
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            running_processes = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split('","')
                if len(parts) >= 2:
                    proc_name = parts[0].replace('"', '')
                    running_processes.append(proc_name.lower())
            
            # 查找匹配的进程名
            app_name_lower = app_name.lower()
            matched_processes = []
            
            # 检查映射表
            for key, process_list in APP_PROCESS_MAPPING.items():
                if app_name_lower == key.lower() or app_name_lower in key.lower():
                    for proc in process_list:
                        if proc.lower() in running_processes:
                            matched_processes.append(proc)
            
            # 如果没有找到，尝试直接匹配
            if not matched_processes:
                direct_match = f"{app_name}.exe"
                if direct_match.lower() in running_processes:
                    matched_processes.append(direct_match)
            
            return matched_processes
            
        except Exception as e:
            logger.error(f"查找运行进程失败: {e}")
            return []

    async def _list_installed_apps(self) -> str:
        """列出已安装的应用"""
        if not self._installed_apps:
            return "📱 未发现已安装的应用"
        
        # 去重并排序
        unique_apps = {}
        for name, path in self._installed_apps.items():
            # 使用原始名称（首字母大写）
            display_name = name.title() if name.islower() else name
            if display_name not in unique_apps:
                unique_apps[display_name] = path
        
        sorted_apps = sorted(unique_apps.items(), key=lambda x: x[0].lower())
        
        # 只显示前30个
        display_list = sorted_apps[:30]
        result = "📱 已安装的应用:\n" + '\n'.join(f"  • {name}" for name, _ in display_list)
        
        if len(sorted_apps) > 30:
            result += f"\n  ... 还有 {len(sorted_apps) - 30} 个应用"
        
        return result

    async def _list_startup_items(self) -> str:
        """列出系统启动项（只显示已启用的）"""
        try:
            if self.system == "Windows":
                startup_items = []
                
                # 获取已禁用的启动项列表
                disabled_items = await self._get_disabled_startup_items()
                
                # 1. 获取当前用户的启动文件夹
                startup_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
                if os.path.exists(startup_folder):
                    for item in os.listdir(startup_folder):
                        if item.endswith(('.lnk', '.exe', '.bat', '.cmd')):
                            name = item.replace('.lnk', '').replace('.exe', '')
                            if name not in disabled_items:
                                startup_items.append({
                                    'name': name,
                                    'path': os.path.join(startup_folder, item),
                                    'source': '启动文件夹',
                                    'enabled': True
                                })
                
                # 2. 获取注册表启动项 (当前用户) - 只添加未被禁用的
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                if name not in disabled_items:
                                    startup_items.append({
                                        'name': name,
                                        'path': value,
                                        'source': '注册表(当前用户)',
                                        'enabled': True
                                    })
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    logger.warning(f"读取当前用户注册表启动项失败: {e}")
                
                # 3. 获取注册表启动项 (所有用户) - 只添加未被禁用的
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                if name not in disabled_items:
                                    startup_items.append({
                                        'name': name,
                                        'path': value,
                                        'source': '注册表(所有用户)',
                                        'enabled': True
                                    })
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    logger.warning(f"读取所有用户注册表启动项失败: {e}")
                
                # 4. 获取 RunOnce 启动项（这些是临时启动项，通常不会被禁用）
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce") as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                startup_items.append({
                                    'name': name,
                                    'path': value,
                                    'source': 'RunOnce(当前用户)',
                                    'enabled': True
                                })
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    logger.warning(f"读取 RunOnce 启动项失败: {e}")
                
                # 格式化输出
                if startup_items:
                    # 去重（根据名称）
                    seen = set()
                    unique_items = []
                    for item in startup_items:
                        if item['name'] not in seen:
                            seen.add(item['name'])
                            unique_items.append(item)
                    
                    # 排序
                    unique_items.sort(key=lambda x: x['name'].lower())
                    
                    # 定义启动项中文名称映射
                    STARTUP_NAME_MAPPING = {
                        'AweSun': '向日葵远程控制',
                        'RtkAudUService': 'Realtek音频服务',
                        'SecurityHealth': 'Windows安全中心',
                        'OneDrive': 'OneDrive云盘',
                        'QQMusic': 'QQ音乐',
                        'Weixin': '微信',
                        'Yuanbao': '腾讯元宝',
                        'doubao': '豆包',
                        'DingTalk': '钉钉',
                        'MicrosoftEdgeAutoLaunch': 'Edge浏览器自动启动',
                        'WindowsDefender': 'Windows Defender',
                        'MsMpEng': 'Windows Defender杀毒',
                        'SearchIndexer': 'Windows搜索索引',
                        'ctfmon': '输入法语言栏',
                        'AdobeARM': 'Adobe更新服务',
                        'GoogleUpdate': 'Google更新服务',
                        'Steam': 'Steam客户端',
                        'EpicGamesLauncher': 'Epic游戏启动器',
                        'Spotify': 'Spotify音乐',
                        'Discord': 'Discord聊天',
                        'Telegram': 'Telegram电报',
                        'Slack': 'Slack协作',
                        'Zoom': 'Zoom会议',
                        'Teams': 'Microsoft Teams',
                        'Skype': 'Skype通话',
                        'Dropbox': 'Dropbox云盘',
                        '坚果云': '坚果云同步',
                        '百度网盘': '百度网盘',
                        '阿里云盘': '阿里云盘',
                        '天翼云盘': '天翼云盘',
                        '迅雷': '迅雷下载',
                        'IDMan': 'IDM下载器',
                        'qBittorrent': 'qBittorrent下载',
                        'uTorrent': 'uTorrent下载',
                        'BitComet': '比特彗星下载',
                        'NVIDIA': 'NVIDIA显卡服务',
                        'AMD': 'AMD显卡服务',
                        'Intel': 'Intel显卡服务',
                        'RadeonSoftware': 'AMD显卡软件',
                        'GeForceExperience': 'NVIDIA GeForce Experience',
                        'MSIAfterburner': '微星小飞机',
                        'HWiNFO': 'HWiNFO硬件监控',
                        'CoreTemp': 'CoreTemp温度监控',
                        'SpeedFan': 'SpeedFan风扇控制',
                        'WallpaperEngine': 'Wallpaper Engine壁纸',
                        'Rainmeter': 'Rainmeter桌面美化',
                        'Fences': 'Fences桌面整理',
                        'Listary': 'Listary快速启动',
                        'Everything': 'Everything搜索',
                        'Wox': 'Wox启动器',
                        'PowerToys': 'PowerToys工具集',
                        'AutoHotkey': 'AutoHotkey脚本',
                        'X-Mouse': 'X-Mouse鼠标设置',
                        'ShareX': 'ShareX截图工具',
                        'Snipaste': 'Snipaste截图',
                        'FastStone': 'FastStone截图',
                        'OBS': 'OBS录屏直播',
                        'Bandicam': 'Bandicam录屏',
                        'Camtasia': 'Camtasia录屏',
                        'PotPlayer': 'PotPlayer播放器',
                        'MPC-HC': 'MPC-HC播放器',
                        'VLC': 'VLC播放器',
                        'Kodi': 'Kodi媒体中心',
                        'Plex': 'Plex媒体服务器',
                        'Emby': 'Emby媒体服务器',
                        'Jellyfin': 'Jellyfin媒体服务器',
                        'Syncthing': 'Syncthing同步',
                        'ResilioSync': 'Resilio Sync同步',
                        'GoodSync': 'GoodSync同步',
                        'FreeFileSync': 'FreeFileSync同步',
                        'MacType': 'MacType字体渲染',
                        'StartIsBack': 'StartIsBack开始菜单',
                        'StartAllBack': 'StartAllBack开始菜单',
                        'OpenShell': 'Open-Shell开始菜单',
                        'ClassicShell': 'ClassicShell开始菜单',
                        '7+TaskbarTweaker': '7+ Taskbar Tweaker任务栏',
                        'TaskbarX': 'TaskbarX任务栏美化',
                        'TranslucentTB': 'TranslucentTB任务栏透明',
                        'RoundedTB': 'RoundedTB任务栏圆角',
                        'EarTrumpet': 'EarTrumpet音量控制',
                        'SoundSwitch': 'SoundSwitch音频切换',
                        'AudioSwitcher': 'AudioSwitcher音频切换',
                        'Voicemeeter': 'Voicemeeter虚拟混音',
                        'VB-Audio': 'VB-Audio虚拟音频',
                        'RTSS': 'RTSS游戏帧数显示',
                        'CapFrameX': 'CapFrameX帧数记录',
                        'PresentMon': 'PresentMon帧数监控',
                        'SpecialK': 'SpecialK游戏优化',
                        'ReShade': 'ReShade游戏滤镜',
                        'GShade': 'GShade游戏滤镜',
                        'Vortex': 'Vortex模组管理',
                        'ModOrganizer': 'Mod Organizer模组管理',
                        'NexusModManager': 'Nexus Mod Manager',
                        'SteamAchievementManager': 'Steam成就管理器',
                        'Depressurizer': 'DepressurizerSteam库管理',
                        'Playnite': 'Playnite游戏库',
                        'GOGGalaxy': 'GOG Galaxy游戏库',
                        'EA': 'EA App游戏平台',
                        'UbisoftConnect': 'Ubisoft Connect游戏平台',
                        'Battle.net': '战网游戏平台',
                        'RiotGames': '拳头游戏平台',
                        'Valorant': '无畏契约',
                        'LeagueOfLegends': '英雄联盟',
                        'Overwolf': 'Overwolf游戏工具',
                        'DiscordCanary': 'Discord测试版',
                        'DiscordPTB': 'Discord预览版',
                        'Element': 'Element聊天',
                        'Signal': 'Signal聊天',
                        'WhatsApp': 'WhatsApp聊天',
                        'Line': 'Line聊天',
                        'KakaoTalk': 'KakaoTalk聊天',
                        'Viber': 'Viber聊天',
                        'WeCom': '企业微信',
                        'DingTalk': '钉钉',
                        'Lark': '飞书',
                        'Feishu': '飞书',
                        'TIM': 'TIM办公版',
                        'QQ': 'QQ聊天',
                        'YY': 'YY语音',
                        'KOOK': 'KOOK语音',
                        'Oopz': 'Oopz语音',
                        'Fanbook': 'Fanbook社区',
                        'NvidiaBroadcast': 'NVIDIA Broadcast',
                        'CamoStudio': 'Camo摄像头',
                        'DroidCam': 'DroidCam手机摄像头',
                        'IriunWebcam': 'Iriun手机摄像头',
                        'EpocCam': 'EpocCam手机摄像头',
                        'FineShare': 'FineShare虚拟摄像头',
                        'ManyCam': 'ManyCam虚拟摄像头',
                        'SplitCam': 'SplitCam虚拟摄像头',
                        'XSplit': 'XSplit直播',
                        'Streamlabs': 'Streamlabs直播',
                        'Restream': 'Restream直播',
                        'PrismLive': 'PrismLive直播',
                        'DouyinLive': '抖音直播伴侣',
                        'BilibiliLive': '哔哩哔哩直播姬',
                        'YYLive': 'YY直播',
                        'HuyaLive': '虎牙直播',
                        'DouyuLive': '斗鱼直播',
                        'KuaishouLive': '快手直播',
                        'iTunesHelper': 'iTunes助手',
                        'iCloud': 'iCloud云盘',
                        'iCloudPhotos': 'iCloud照片',
                        'iCloudDrive': 'iCloud云盘',
                        'AppleMobileDeviceService': 'Apple移动设备服务',
                        'Bonjour': 'Bonjour服务',
                        'AdobeCreativeCloud': 'Adobe Creative Cloud',
                        'AdobeGCClient': 'Adobe正版验证',
                        'CCXProcess': 'Adobe CCX进程',
                        'CoreSync': 'Adobe同步',
                        'AcrobatAssistant': 'Adobe Acrobat助手',
                        'AdobeUpdaterStartupUtility': 'Adobe更新工具',
                        'SpotifyWebHelper': 'Spotify网页助手',
                        'AmazonMusic': 'Amazon音乐',
                        'TIDAL': 'TIDAL音乐',
                        'Deezer': 'Deezer音乐',
                        'YouTubeMusic': 'YouTube音乐',
                        'Netflix': 'Netflix应用',
                        'DisneyPlus': 'Disney+应用',
                        'AmazonPrimeVideo': 'Prime Video',
                        'HBO': 'HBO Max',
                        'Hulu': 'Hulu应用',
                        'AppleTV': 'Apple TV+',
                        'Peacock': 'Peacock应用',
                        'ParamountPlus': 'Paramount+',
                        'Crunchyroll': 'Crunchyroll动漫',
                        'Funimation': 'Funimation动漫',
                        'VRV': 'VRV动漫',
                        'HIDIVE': 'HIDIVE动漫',
                        'Bilibili': '哔哩哔哩',
                        'AcFun': 'AcFun弹幕',
                        'Niconico': 'Niconico弹幕',
                        'Youku': '优酷',
                        'iQiyi': '爱奇艺',
                        'TencentVideo': '腾讯视频',
                        'MangoTV': '芒果TV',
                        'SohuVideo': '搜狐视频',
                        'LeTV': '乐视视频',
                        'PPTV': 'PPTV聚力',
                        'CCTV': '央视影音',
                        'Xiaomi': '小米服务',
                        'Huawei': '华为服务',
                        'OPPO': 'OPPO服务',
                        'Vivo': 'vivo服务',
                        'Realme': 'realme服务',
                        'OnePlus': '一加服务',
                        'Samsung': '三星服务',
                        'LG': 'LG服务',
                        'Sony': '索尼服务',
                        'Asus': '华硕服务',
                        'Acer': '宏碁服务',
                        'Dell': '戴尔服务',
                        'HP': '惠普服务',
                        'Lenovo': '联想服务',
                        'MSI': '微星服务',
                        'Gigabyte': '技嘉服务',
                        'ASRock': '华擎服务',
                        'Corsair': '海盗船服务',
                        'Razer': '雷蛇服务',
                        'Logitech': '罗技服务',
                        'SteelSeries': '赛睿服务',
                        'HyperX': 'HyperX服务',
                        'CoolerMaster': '酷冷至尊服务',
                        'Thermaltake': '曜越服务',
                        'NZXT': 'NZXT服务',
                        'EVGA': 'EVGA服务',
                        'Zotac': '索泰服务',
                        'Palit': '同德服务',
                        'Gainward': '耕升服务',
                        'Inno3D': '映众服务',
                        'Colorful': '七彩虹服务',
                        'Galax': '影驰服务',
                        'Maxsun': '铭瑄服务',
                        'Yeston': '盈通服务',
                        'BioStar': '映泰服务',
                        'ECS': '精英服务',
                    }
                    
                    # 显示前20个
                    display_items = unique_items[:20]
                    lines = []
                    for item in display_items:
                        name = item['name']
                        source = item['source']
                        # 尝试匹配中文名称
                        chinese_name = None
                        for key, value in STARTUP_NAME_MAPPING.items():
                            if key.lower() in name.lower():
                                chinese_name = value
                                break
                        if chinese_name:
                            lines.append(f"  • {chinese_name} ({source})")
                        else:
                            lines.append(f"  • {name} ({source})")
                    
                    result = f"🚀 已启用的启动项 (共{len(unique_items)}个):\n" + '\n'.join(lines)
                    
                    if len(unique_items) > 20:
                        result += f"\n  ... 还有 {len(unique_items) - 20} 个启动项"
                    
                    if disabled_items:
                        result += f"\n\n💡 提示: 还有 {len(disabled_items)} 个启动项已被禁用"
                    
                    return result
                else:
                    if disabled_items:
                        return f"🚀 当前没有启用的启动项\n💡 有 {len(disabled_items)} 个启动项已被禁用"
                    else:
                        return "🚀 暂无开机启动项"
            else:
                # Linux/macOS: 使用 systemctl 或 launchctl
                if self.system == "Linux":
                    result = subprocess.run(
                        ["systemctl", "list-unit-files", "--type=service", "--state=enabled"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')[1:-7]  # 去掉标题和底部信息
                        services = [line.split()[0] for line in lines if line.strip()]
                        if services:
                            display_list = services[:20]
                            return "🚀 开机启动服务:\n" + '\n'.join(f"  • {s}" for s in display_list)
                        else:
                            return "🚀 暂无开机启动服务"
                
                return f"🚀 暂不支持 {self.system} 系统的启动项查看"
                
        except Exception as e:
            logger.error(f"获取启动项失败: {e}")
            return f"❌ 获取启动项失败: {str(e)}"

    async def _get_disabled_startup_items(self) -> set:
        """获取已被禁用的启动项名称集合"""
        disabled = set()
        try:
            # 方法1: 通过 WMI 查询启动项状态 (Windows 8+)
            try:
                import subprocess
                result = subprocess.run(
                    ["wmic", "startup", "get", "Caption,Command,Location,User", "/format:csv"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # 注意: wmic 在新版 Windows 中可能被移除，失败时继续尝试其他方法
            except Exception:
                pass
            
            # 方法2: 检查注册表中标记为禁用的启动项
            # Windows 任务管理器禁用的启动项通常会在以下位置记录
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run") as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            # 如果值为二进制且第一个字节是 0x00 或 0x01，表示已禁用
                            if isinstance(value, bytes) and len(value) > 0:
                                if value[0] in (0x00, 0x01):
                                    disabled.add(name)
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass
            
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run") as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if isinstance(value, bytes) and len(value) > 0:
                                if value[0] in (0x00, 0x01):
                                    disabled.add(name)
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass
            
            # 检查 StartupApproved\StartupFolder
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder") as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if isinstance(value, bytes) and len(value) > 0:
                                if value[0] in (0x00, 0x01):
                                    disabled.add(name.replace('.lnk', '').replace('.exe', ''))
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"获取禁用启动项失败: {e}")

        return disabled

    async def _disable_startup_item(self, app_name: Optional[str]) -> str:
        """禁用启动项"""
        if not app_name:
            return "❌ 请提供要禁用的启动项名称"

        try:
            if self.system == "Windows":
                # 先查找启动项的实际位置和名称
                startup_info = await self._find_startup_item(app_name)

                if not startup_info:
                    return f"⚠️ 未找到启动项: {app_name}"

                item_name = startup_info['name']
                location = startup_info['location']

                # 根据位置禁用启动项
                if location == 'registry_hkcu_run':
                    # 从当前用户注册表 Run 中删除
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                            winreg.KEY_WRITE) as key:
                            winreg.DeleteValue(key, item_name)
                        return f"✅ 已禁用启动项: {app_name}"
                    except Exception as e:
                        logger.error(f"删除注册表启动项失败: {e}")
                        return f"❌ 禁用启动项失败: {str(e)}"

                elif location == 'registry_hklm_run':
                    # 从所有用户注册表 Run 中删除（需要管理员权限）
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                            winreg.KEY_WRITE) as key:
                            winreg.DeleteValue(key, item_name)
                        return f"✅ 已禁用启动项: {app_name}"
                    except PermissionError:
                        return f"⚠️ 禁用启动项需要管理员权限: {app_name}"
                    except Exception as e:
                        logger.error(f"删除注册表启动项失败: {e}")
                        return f"❌ 禁用启动项失败: {str(e)}"

                elif location == 'startup_folder':
                    # 从启动文件夹中删除快捷方式
                    try:
                        startup_folder = os.path.expandvars(
                            r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
                        for ext in ['.lnk', '.exe', '.bat', '.cmd']:
                            file_path = os.path.join(startup_folder, item_name + ext)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                return f"✅ 已禁用启动项: {app_name}"
                        return f"⚠️ 未找到启动项文件: {app_name}"
                    except Exception as e:
                        logger.error(f"删除启动文件夹项失败: {e}")
                        return f"❌ 禁用启动项失败: {str(e)}"

                else:
                    # 对于其他位置，尝试在 StartupApproved 中标记为禁用
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                                            0, winreg.KEY_WRITE) as key:
                            # 写入禁用标记 (0x00 表示禁用)
                            winreg.SetValueEx(key, item_name, 0, winreg.REG_BINARY, b'\x00' + b'\x00' * 11)
                        return f"✅ 已禁用启动项: {app_name}"
                    except Exception as e:
                        logger.error(f"标记启动项为禁用失败: {e}")
                        return f"❌ 禁用启动项失败: {str(e)}"

            else:
                return f"🚀 暂不支持 {self.system} 系统的启动项管理"

        except Exception as e:
            logger.error(f"禁用启动项失败: {e}")
            return f"❌ 禁用启动项失败: {str(e)}"

    async def _enable_startup_item(self, app_name: Optional[str]) -> str:
        """启用启动项"""
        if not app_name:
            return "❌ 请提供要启用的启动项名称"

        try:
            if self.system == "Windows":
                # 先检查是否在 StartupApproved 中被标记为禁用
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                                        0, winreg.KEY_WRITE) as key:
                        # 尝试删除禁用标记（如果存在）
                        try:
                            winreg.DeleteValue(key, app_name)
                        except FileNotFoundError:
                            pass
                except Exception:
                    pass

                # 尝试在 StartupApproved\Run 中标记为启用
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                                        0, winreg.KEY_WRITE) as key:
                        # 写入启用标记 (0x02 表示启用)
                        winreg.SetValueEx(key, app_name, 0, winreg.REG_BINARY, b'\x02' + b'\x00' * 11)
                except Exception as e:
                    logger.warning(f"标记启动项为启用失败: {e}")

                return f"✅ 已启用启动项: {app_name}\n💡 注意：如果该程序之前被从启动列表中删除，需要重新添加"

            else:
                return f"🚀 暂不支持 {self.system} 系统的启动项管理"

        except Exception as e:
            logger.error(f"启用启动项失败: {e}")
            return f"❌ 启用启动项失败: {str(e)}"

    async def _find_startup_item(self, app_name: str) -> Optional[Dict]:
        """查找启动项的详细信息"""
        try:
            app_name_lower = app_name.lower()

            # 中文名称到原始名称的反向映射
            REVERSE_NAME_MAPPING = {
                '向日葵远程控制': ['AweSun'],
                '向日葵': ['AweSun'],
                'realtek音频服务': ['RtkAudUService'],
                'windows安全中心': ['SecurityHealth'],
                'onedrive云盘': ['OneDrive'],
                'qq音乐': ['QQMusic'],
                '微信': ['Weixin'],
                '腾讯元宝': ['Yuanbao'],
                '豆包': ['doubao'],
                '钉钉': ['DingTalk'],
                'edge浏览器自动启动': ['MicrosoftEdgeAutoLaunch'],
            }

            # 获取可能的原始名称列表
            possible_names = [app_name_lower]
            for chinese_name, english_names in REVERSE_NAME_MAPPING.items():
                if app_name_lower in chinese_name.lower():
                    possible_names.extend([n.lower() for n in english_names])

            # 1. 检查当前用户注册表 Run
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            name_lower = name.lower()
                            # 检查是否匹配任何可能的名称
                            for possible_name in possible_names:
                                if possible_name in name_lower:
                                    return {'name': name, 'path': value, 'location': 'registry_hkcu_run'}
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass

            # 2. 检查所有用户注册表 Run
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            name_lower = name.lower()
                            # 检查是否匹配任何可能的名称
                            for possible_name in possible_names:
                                if possible_name in name_lower:
                                    return {'name': name, 'path': value, 'location': 'registry_hklm_run'}
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass

            # 3. 检查启动文件夹
            startup_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
            if os.path.exists(startup_folder):
                for item in os.listdir(startup_folder):
                    item_base = item.replace('.lnk', '').replace('.exe', '').lower()
                    # 检查是否匹配任何可能的名称
                    for possible_name in possible_names:
                        if possible_name in item_base:
                            return {'name': item.replace('.lnk', '').replace('.exe', ''),
                                    'path': os.path.join(startup_folder, item), 'location': 'startup_folder'}

            return None

        except Exception as e:
            logger.error(f"查找启动项失败: {e}")
            return None

    async def _list_running_apps(self) -> str:
        """列出正在运行的应用"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # 系统进程列表（需要过滤掉的）
                    system_processes = {
                        'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe',
                        'lsass.exe', 'svchost.exe', 'fontdrvhost.exe', 'dwm.exe', 'WUDFHost.exe',
                        'LsaIso.exe', 'Registry', 'System', 'System Idle Process', 'Memory Compression',
                        'Secure System', 'Idle', 'taskhostw.exe', 'sihost.exe', 'explorer.exe',
                        'StartMenuExperienceHost.exe', 'SearchIndexer.exe', 'SearchProtocolHost.exe',
                        'RuntimeBroker.exe', 'ShellExperienceHost.exe', 'TextInputHost.exe',
                        'Widgets.exe', 'WidgetService.exe', 'backgroundTaskHost.exe',
                        'ApplicationFrameHost.exe', 'dllhost.exe', 'ctfmon.exe',
                        'conhost.exe', 'WmiPrvSE.exe', 'WMIADAP.exe', 'WMIC.exe',
                        'spoolsv.exe', 'wlanext.exe', 'conhost.exe', 'SearchHost.exe',
                        'TiWorker.exe', 'TrustedInstaller.exe', 'CompatTelRunner.exe',
                        'MusNotification.exe', 'MusNotifyIcon.exe', 'OneDrive.exe',
                        'SecurityHealthSystray.exe', 'SecurityHealthService.exe',
                        'SettingSyncHost.exe', 'DeviceCensus.exe', 'MoUsoCoreWorker.exe',
                        'UpdateAssistant.exe', 'WindowsUpdateBox.exe', 'SetupHost.exe',
                        'SetupPrep.exe', 'SystemSettings.exe', 'UserOOBEBroker.exe',
                        'Video.UI.exe', 'WebViewHost.exe', 'WindowsTerminal.exe',
                        'OpenConsole.exe', 'powershell.exe', 'cmd.exe', 'python.exe',
                        'pythonw.exe', 'py.exe', 'Trae.exe', 'Code.exe', 'chrome.exe',
                        'msedge.exe', 'firefox.exe',
                        # 新增的后台服务进程
                        'CrossDeviceResume.exe', 'ShellHost.exe', 'OneApp.IGCC.WinService.exe',
                        'HMSCoreContainer.exe', 'WindowsPackageManagerServer.exe',
                        'RtkAudUService64.exe', 'MidiSrv.exe', 'wslservice.exe',
                        'MpDefenderCoreService.exe', 'QiyiService.exe', 'audiodg.exe',
                        'LMS.exe', 'igfxEM.exe', 'AggregatorHost.exe', 'IntelCpHDCPSvc.exe',
                        'IntelCpHeciSvc.exe', 'jhi_service.exe', 'esif_uf.exe', 'RstMwService.exe',
                        'RtkBtManServ.exe', 'RAVBg64.exe', 'RAVCpl64.exe', 'IAStorDataMgrSvc.exe',
                        'IntelAudioService.exe', 'IntelWirelessBluetooth.exe', 'SgrmBroker.exe',
                        'WpnService.exe', 'WpnUserService.exe', 'cplspcon.exe', 'igfxCUIService.exe',
                        'PresentationFontCache.exe', 'FMAPOService.exe', 'HPPrintScanDoctorService.exe',
                        'HPSupportSolutionsFrameworkService.exe', 'HPSystemEventUtilityHost.exe',
                        'HPCommRecovery.exe', 'HPAnalyticsService.exe', 'HPAppHelperCap.exe',
                        'HPDiagsCap.exe', 'HPNetworkCap.exe', 'HPPrintScanDoctor.exe',
                        'HPScanDoctor.exe', 'HPSecureBrowser.exe', 'HPSetup.exe', 'HPSF.exe',
                        'HPSF_Utils.exe', 'HPSF_Worker.exe', 'HPSF_Service.exe', 'HPSF_Tasks.exe',
                        'HPSF_Updater.exe', 'HPSF_Watcher.exe', 'HPSF_Worker.exe'
                    }
                    
                    lines = result.stdout.strip().split('\n')
                    apps = []
                    for line in lines:
                        parts = line.split('","')
                        if len(parts) >= 2:
                            app_name = parts[0].replace('"', '')
                            # 过滤系统进程和常见后台进程
                            if app_name.endswith('.exe') and app_name not in system_processes:
                                # 获取内存使用信息
                                mem_info = parts[4].replace('"', '').replace(' K', '').replace(',', '') if len(parts) > 4 else '0'
                                try:
                                    mem_mb = int(mem_info) / 1024 if mem_info.isdigit() else 0
                                    # 只显示使用内存大于10MB的应用（过滤掉小进程）
                                    if mem_mb > 10:
                                        apps.append((app_name, mem_mb))
                                except:
                                    apps.append((app_name, 0))
                    
                    # 合并相同应用的进程，统计进程数和总内存
                    from collections import defaultdict
                    app_stats = defaultdict(lambda: {'count': 0, 'total_mem': 0, 'max_mem': 0})
                    
                    for app_name, mem_mb in apps:
                        # 标准化应用名称（去掉.exe后缀，统一名称）
                        base_name = app_name.replace('.exe', '')
                        # 统一一些常见应用的名称
                        name_mapping = {
                            'Trae CN': 'Trae',
                            'Trae': 'Trae',
                            'Weixin': '微信',
                            'WeChat': '微信',
                            'WeChatAppEx': '微信小程序',
                            'msedgewebview2': 'Edge WebView',
                            'chrome': 'Chrome',
                            'firefox': 'Firefox',
                            'msedge': 'Edge',
                            'Code': 'VS Code',
                            'yuanbao': '腾讯元宝',
                            'MsMpEng': 'Windows Defender',
                            'MpDefenderCoreService': None,  # 过滤掉
                            'CrossDeviceResume': None,
                            'ShellHost': None,
                            'OneAppIGCCWinService': None,
                            'HMSCoreContainer': None,
                            'WindowsPackageManagerServer': None,
                            'RtkAudUService64': None,
                            'MidiSrv': None,
                            'wslservice': None,
                            'QiyiService': None,
                            'audiodg': None,
                            'LMS': None,
                            'igfxEM': None,
                            'AggregatorHost': None,
                        }
                        mapped_name = name_mapping.get(base_name)
                        if mapped_name is None:
                            continue  # 跳过不需要显示的后台进程
                        display_name = mapped_name if mapped_name else base_name
                        
                        app_stats[display_name]['count'] += 1
                        app_stats[display_name]['total_mem'] += mem_mb
                        app_stats[display_name]['max_mem'] = max(app_stats[display_name]['max_mem'], mem_mb)
                    
                    # 转换为列表并按总内存排序
                    app_list = []
                    for name, stats in app_stats.items():
                        app_list.append({
                            'name': name,
                            'count': stats['count'],
                            'total_mem': stats['total_mem'],
                            'max_mem': stats['max_mem']
                        })
                    
                    app_list.sort(key=lambda x: x['total_mem'], reverse=True)
                    app_list = app_list[:20]  # 取前20个
                    
                    if app_list:
                        # 格式化输出
                        formatted_apps = []
                        for app in app_list:
                            name = app['name']
                            count = app['count']
                            total_mem = app['total_mem']
                            
                            if count > 1:
                                # 多个进程时显示进程数和总内存
                                formatted_apps.append(f"{name} ({count}个进程, 共{total_mem:.0f}MB)")
                            else:
                                # 单个进程时只显示内存
                                formatted_apps.append(f"{name} ({total_mem:.0f}MB)")
                        
                        return "📱 正在运行的应用:\n" + '\n'.join(f"  • {app}" for app in formatted_apps)
                    else:
                        return "📱 暂无运行中的应用"
            else:
                result = subprocess.run(
                    ["ps", "-eo", "comm,pid,pcpu,pmem", "--sort=-pmem"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:21]  # 跳过标题，取前20个
                    apps = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4:
                            app_name = parts[0]
                            mem_usage = parts[3]
                            if app_name not in ['ps', 'bash', 'sh', 'zsh', 'fish']:
                                apps.append(f"{app_name} ({mem_usage}%)")
                    
                    return "📱 正在运行的应用:\n" + '\n'.join(f"  • {app}" for app in apps)
            
            return "❌ 无法获取运行中的应用列表"
            
        except Exception as e:
            logger.error(f"获取运行中的应用列表失败: {e}")
            return f"❌ 获取应用列表失败: {str(e)}"

    async def _is_running(self, app_name: Optional[str]) -> str:
        """检查应用是否正在运行"""
        if not app_name:
            return "❌ 请提供应用名称"
        
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {app_name}.exe"],
                    capture_output=True,
                    text=True
                )
                
                if app_name.lower() + ".exe" in result.stdout.lower():
                    return f"✅ {app_name} 正在运行"
                else:
                    return f"📱 {app_name} 未运行"
            else:
                result = subprocess.run(
                    ["pgrep", "-f", app_name],
                    capture_output=True
                )
                
                if result.returncode == 0:
                    return f"✅ {app_name} 正在运行"
                else:
                    return f"📱 {app_name} 未运行"
                    
        except Exception as e:
            logger.error(f"检查应用状态失败: {e}")
            return f"❌ 检查应用状态失败: {str(e)}"

    def get_capabilities(self) -> list:
        """获取能力列表"""
        return [
            "app_management",
            "file_open",
            "process_control"
        ]

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 应用智能体

### 功能说明
应用智能体可以控制电脑上的第三方应用程序，支持打开、关闭、安装软件等操作。

### 支持的操作
- **打开应用**：启动已安装的应用程序
- **关闭应用**：关闭正在运行的应用程序
- **安装应用**：下载并安装新的软件
- **查看运行中的应用**：列出当前正在运行的程序
- **查看已安装应用**：列出电脑上已安装的软件

### 使用示例
- "打开微信" - 启动微信应用
- "打开 Chrome" - 启动 Chrome 浏览器
- "关闭 QQ" - 关闭 QQ 应用
- "安装 VS Code" - 下载并安装 VS Code
- "查看运行中的应用" - 列出当前运行的程序
- "查看已安装的应用" - 列出已安装的软件

### 支持的应用类型
- 浏览器：Chrome、Edge、Firefox、QQ浏览器等
- 办公软件：WPS、Office、VS Code、记事本等
- 社交软件：QQ、微信、钉钉等
- 媒体软件：QQ音乐、网易云音乐、酷狗音乐等
- 工具软件：计算器、画图、截图工具等

### 注意事项
- 部分软件需要管理员权限才能打开或关闭
- 安装软件时需要联网
- 如果应用未找到，会尝试自动安装"""
