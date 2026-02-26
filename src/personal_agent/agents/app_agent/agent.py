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
            elif action == "close":
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
            elif action == "list_installed":
                return await self._list_installed_apps()
            elif action == "list_running":
                return await self._list_running_apps()
            elif action == "is_running":
                return await self._is_running(params.get("app_name"))
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
                # 使用 taskkill 关闭进程
                # 尝试通过进程名关闭
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
                    lines = result.stdout.strip().split('\n')[:20]  # 只显示前20个
                    apps = []
                    for line in lines:
                        parts = line.split('","')
                        if len(parts) >= 2:
                            app_name = parts[0].replace('"', '')
                            if app_name.endswith('.exe'):
                                apps.append(app_name)
                    
                    if apps:
                        return "📱 正在运行的应用:\n" + '\n'.join(f"  • {app}" for app in apps)
                    else:
                        return "📱 暂无运行中的应用"
            else:
                result = subprocess.run(
                    ["ps", "-eo", "comm"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    apps = list(set(result.stdout.strip().split('\n')[1:]))[:20]
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
