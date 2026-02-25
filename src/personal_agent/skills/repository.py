"""
Skills Repository Manager - Download and manage OpenClaw skills
"""
import asyncio
import json
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import aiohttp

logger = logging.getLogger(__name__)

SKILLS_REGISTRY_URL = "https://raw.githubusercontent.com/openclaw/skills/main/registry.json"
OPENCLAW_SKILLS_REPO = "https://api.github.com/repos/openclaw/skills/contents"
GITHUB_RAW_URL = "https://raw.githubusercontent.com"


@dataclass
class SkillInfo:
    """Skill information from repository"""
    name: str
    description: str
    author: str = ""
    version: str = "1.0.0"
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    github_url: str = ""
    download_url: str = ""
    installed: bool = False
    local_path: Optional[Path] = None


class SkillsRepository:
    """Manage skills from OpenClaw repository"""
    
    BUILTIN_SKILLS = [
        {
            "name": "weather-query",
            "description": "查询全球主要城市实时天气，支持中文查询",
            "author": "Personal Agent",
            "version": "1.0.0",
            "category": "utility",
            "tags": ["天气", "查询", "weather"],
        },
        {
            "name": "generate-qr-code",
            "description": "生成二维码，支持文本、URL等内容",
            "author": "Personal Agent",
            "version": "1.0.0",
            "category": "utility",
            "tags": ["二维码", "QR", "生成"],
        },
        {
            "name": "file-manager",
            "description": "文件管理工具，支持文件搜索、复制、移动、删除等操作",
            "author": "Personal Agent",
            "version": "1.0.0",
            "category": "system",
            "tags": ["文件", "管理", "file"],
        },
        {
            "name": "system-info",
            "description": "系统信息查询工具，获取CPU、内存、磁盘等状态",
            "author": "Personal Agent",
            "version": "1.0.0",
            "category": "system",
            "tags": ["系统", "信息", "system"],
        },
        {
            "name": "web-search",
            "description": "网络搜索工具，搜索实时信息",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "web",
            "tags": ["搜索", "网络", "search"],
        },
        {
            "name": "email-assistant",
            "description": "邮件助手，帮助管理和发送邮件",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "productivity",
            "tags": ["邮件", "email", "助手"],
        },
        {
            "name": "calendar",
            "description": "日历管理，添加和查询日程安排",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "productivity",
            "tags": ["日历", "日程", "calendar"],
        },
        {
            "name": "code-review",
            "description": "代码审查助手，分析和改进代码质量",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "development",
            "tags": ["代码", "审查", "review"],
        },
        {
            "name": "translator",
            "description": "翻译助手，支持多语言翻译",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "utility",
            "tags": ["翻译", "translate", "语言"],
        },
        {
            "name": "reminder",
            "description": "提醒助手，设置和管理提醒事项",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "productivity",
            "tags": ["提醒", "reminder", "待办"],
        },
        {
            "name": "note-taking",
            "description": "笔记管理，创建和组织笔记",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "productivity",
            "tags": ["笔记", "note", "记录"],
        },
        {
            "name": "github-assistant",
            "description": "GitHub助手，管理仓库和PR",
            "author": "OpenClaw Community",
            "version": "1.0.0",
            "category": "development",
            "tags": ["github", "仓库", "开发"],
        },
    ]
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, SkillInfo] = {}
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        self._progress_callback = callback
    
    async def _report_progress(self, message: str, progress: int = -1):
        if self._progress_callback:
            import asyncio
            if asyncio.iscoroutinefunction(self._progress_callback):
                await self._progress_callback(message, progress)
            else:
                self._progress_callback(message, progress)
    
    async def fetch_available_skills(self) -> List[SkillInfo]:
        """Fetch available skills from repository"""
        skills = []
        
        await self._report_progress("正在获取技能列表...", 10)
        
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        OPENCLAW_SKILLS_REPO,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for item in data:
                                if item.get("type") == "dir":
                                    skill_info = SkillInfo(
                                        name=item.get("name", ""),
                                        description=f"来自OpenClaw社区",
                                        github_url=item.get("url", ""),
                                        download_url=item.get("html_url", ""),
                                    )
                                    skills.append(skill_info)
                except Exception as e:
                    logger.warning(f"Failed to fetch from GitHub: {e}")
        except Exception as e:
            logger.warning(f"Network error: {e}")
        
        await self._report_progress("加载内置技能列表...", 50)
        
        for builtin in self.BUILTIN_SKILLS:
            skill_info = SkillInfo(
                name=builtin["name"],
                description=builtin["description"],
                author=builtin.get("author", ""),
                version=builtin.get("version", "1.0.0"),
                category=builtin.get("category", "general"),
                tags=builtin.get("tags", []),
            )
            skills.append(skill_info)
        
        await self._report_progress("检查已安装技能...", 80)
        
        installed_skills = self._get_installed_skills()
        for skill in skills:
            skill.installed = skill.name in installed_skills
            if skill.installed:
                skill.local_path = self.skills_dir / skill.name
        
        await self._report_progress("完成", 100)
        
        self._cache = {s.name: s for s in skills}
        return skills
    
    def _get_installed_skills(self) -> List[str]:
        """Get list of installed skills"""
        installed = []
        if self.skills_dir.exists():
            for item in self.skills_dir.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    installed.append(item.name)
        return installed
    
    def get_skill_info(self, name: str) -> Optional[SkillInfo]:
        """Get skill info by name"""
        return self._cache.get(name)
    
    async def download_skill(
        self,
        skill_name: str,
        source: str = "builtin"
    ) -> Dict[str, Any]:
        """Download and install a skill"""
        await self._report_progress(f"正在下载 {skill_name}...", 10)
        
        skill_info = self.get_skill_info(skill_name)
        if not skill_info:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}"
            }
        
        if skill_info.installed:
            return {
                "success": True,
                "message": f"Skill {skill_name} is already installed",
                "path": str(skill_info.local_path)
            }
        
        skill_path = self.skills_dir / skill_name
        
        try:
            if source == "builtin" or not skill_info.github_url:
                await self._report_progress("创建技能文件...", 30)
                result = await self._create_builtin_skill(skill_name, skill_path)
            else:
                await self._report_progress("从GitHub下载...", 30)
                result = await self._download_from_github(skill_info, skill_path)
            
            if result["success"]:
                skill_info.installed = True
                skill_info.local_path = skill_path
                
                await self._report_progress("安装完成！", 100)
                
                return {
                    "success": True,
                    "message": f"Skill {skill_name} installed successfully",
                    "path": str(skill_path)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to download skill {skill_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_builtin_skill(self, skill_name: str, skill_path: Path) -> Dict[str, Any]:
        """Create a built-in skill"""
        builtin_data = {s["name"]: s for s in self.BUILTIN_SKILLS}
        
        if skill_name not in builtin_data:
            return {
                "success": False,
                "error": f"Built-in skill not found: {skill_name}"
            }
        
        skill_data = builtin_data[skill_name]
        skill_path.mkdir(parents=True, exist_ok=True)
        
        skill_md_content = f"""---
name: {skill_data['name']}
description: {skill_data['description']}
version: {skill_data.get('version', '1.0.0')}
author: {skill_data.get('author', 'Personal Agent')}
permissions: 根据功能需要
---

# {skill_data['name'].replace('-', ' ').title()} Skill

## 1. Description
{skill_data['description']}

## 2. When to use
- 用户请求相关功能时使用此技能

## 3. How to use
1. 分析用户需求
2. 执行相应操作
3. 返回结果给用户

## 4. Edge cases
- 遇到错误时提供友好的错误信息
"""
        
        (skill_path / "SKILL.md").write_text(skill_md_content, encoding='utf-8')
        
        return {"success": True}
    
    async def _download_from_github(
        self,
        skill_info: SkillInfo,
        skill_path: Path
    ) -> Dict[str, Any]:
        """Download skill from GitHub"""
        try:
            async with aiohttp.ClientSession() as session:
                repo_url = f"https://api.github.com/repos/openclaw/skills/contents/{skill_info.name}"
                
                async with session.get(repo_url) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Failed to fetch skill contents: {response.status}"
                        }
                    
                    contents = await response.json()
                    
                    skill_path.mkdir(parents=True, exist_ok=True)
                    
                    for item in contents:
                        if item["type"] == "file":
                            await self._download_file(session, item, skill_path)
                        elif item["type"] == "dir":
                            await self._download_directory(session, item, skill_path)
                    
                    return {"success": True}
                    
        except Exception as e:
            logger.error(f"GitHub download error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _download_file(
        self,
        session: aiohttp.ClientSession,
        item: dict,
        dest_path: Path
    ):
        """Download a single file from GitHub"""
        download_url = item.get("download_url")
        if not download_url:
            return
        
        async with session.get(download_url) as response:
            if response.status == 200:
                content = await response.text()
                file_path = dest_path / item["name"]
                file_path.write_text(content, encoding='utf-8')
    
    async def _download_directory(
        self,
        session: aiohttp.ClientSession,
        item: dict,
        dest_path: Path
    ):
        """Download a directory from GitHub"""
        dir_path = dest_path / item["name"]
        dir_path.mkdir(parents=True, exist_ok=True)
        
        async with session.get(item["url"]) as response:
            if response.status == 200:
                contents = await response.json()
                for sub_item in contents:
                    if sub_item["type"] == "file":
                        await self._download_file(session, sub_item, dir_path)
    
    async def uninstall_skill(self, skill_name: str) -> Dict[str, Any]:
        """Uninstall a skill"""
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists():
            return {
                "success": False,
                "error": f"Skill not installed: {skill_name}"
            }
        
        try:
            shutil.rmtree(skill_path)
            
            if skill_name in self._cache:
                self._cache[skill_name].installed = False
                self._cache[skill_name].local_path = None
            
            return {
                "success": True,
                "message": f"Skill {skill_name} uninstalled successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_installed_skills(self) -> List[SkillInfo]:
        """Get list of installed skills"""
        return [s for s in self._cache.values() if s.installed]
    
    def get_categories(self) -> List[str]:
        """Get list of skill categories"""
        categories = set()
        for skill in self._cache.values():
            categories.add(skill.category)
        return sorted(list(categories))


skills_repository = SkillsRepository(Path("skills"))
