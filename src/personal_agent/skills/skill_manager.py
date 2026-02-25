"""
OpenClaw Skills Compatibility System
Compatible with OpenClaw's SKILL.md format and AgentSkills.io standard

Features:
- Three-level progressive disclosure (card, detail, full)
- Hot reload support
- AI self-generating skills
"""
import asyncio
import hashlib
import importlib.util
import json
import logging
import re
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
from datetime import datetime
from loguru import logger


class SkillType(Enum):
    SIMPLE = "simple"
    CODE = "code"
    HYBRID = "hybrid"


class DisclosureLevel(Enum):
    CARD = "card"
    DETAIL = "detail"
    FULL = "full"


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    requires: Dict[str, Any] = field(default_factory=dict)
    install: List[Dict[str, Any]] = field(default_factory=list)
    os: List[str] = field(default_factory=list)
    emoji: str = ""
    primary_env: str = ""


@dataclass
class SkillDefinition:
    metadata: SkillMetadata
    description: str = ""
    help: str = ""
    when_to_use: List[str] = field(default_factory=list)
    how_to_use: str = ""
    implementation: Optional[str] = None
    edge_cases: List[str] = field(default_factory=list)
    skill_type: SkillType = SkillType.SIMPLE
    executor: Optional[Callable] = None
    skill_path: Optional[Path] = None
    file_hash: str = ""
    loaded_at: datetime = field(default_factory=datetime.now)


class SkillParser:
    """Parse OpenClaw SKILL.md files (AgentSkills.io compatible)"""
    
    SECTION_PATTERNS = {
        'description': [r'##\s*1\.\s*Description', r'##\s*Description', r'##\s*简介'],
        'help': [r'##\s*Help', r'##\s*帮助', r'##\s*用户帮助'],
        'when_to_use': [r'##\s*2\.\s*When\s+to\s+use', r'##\s*When\s+to\s+use', r'##\s*触发场景', r'##\s*使用场景'],
        'how_to_use': [r'##\s*3\.\s*How\s+to\s+use', r'##\s*How\s+to\s+use', r'##\s*调用逻辑', r'##\s*使用方法'],
        'implementation': [r'##\s*4\.\s*Implementation', r'##\s*Implementation', r'##\s*代码关联'],
        'edge_cases': [r'##\s*5\.\s*Edge\s+cases', r'##\s*Edge\s+cases', r'##\s*边缘场景', r'##\s*注意事项'],
    }
    
    @classmethod
    def parse_file(cls, skill_path: Path) -> Optional[SkillDefinition]:
        """Parse a SKILL.md file or .md file directly"""
        skill_md = skill_path
        
        if skill_path.is_dir():
            skill_md = skill_path / "SKILL.md"
        
        if not skill_md.exists() or not skill_md.is_file():
            logger.debug(f"Skill file not found: {skill_path}")
            return None
        
        if not skill_md.suffix == '.md':
            logger.warning(f"Not a markdown file: {skill_path}")
            return None
        
        try:
            content = skill_md.read_text(encoding='utf-8')
            file_hash = hashlib.md5(content.encode()).hexdigest()
            skill = cls.parse_content(content, skill_path)
            skill.file_hash = file_hash
            return skill
        except Exception as e:
            logger.error(f"Error parsing skill {skill_path}: {e}")
            return None
    
    @classmethod
    def parse_content(cls, content: str, skill_path: Optional[Path] = None) -> SkillDefinition:
        """Parse SKILL.md content"""
        metadata = cls._parse_metadata(content)
        sections = cls._parse_sections(content)
        
        skill_type = SkillType.SIMPLE
        executor = None
        
        if skill_path:
            agent_py = skill_path / "agent.py"
            index_ts = skill_path / "index.ts"
            
            if agent_py.exists():
                skill_type = SkillType.CODE
                executor = cls._load_python_executor(agent_py, metadata.name)
            elif index_ts.exists():
                skill_type = SkillType.CODE
                logger.warning(f"TypeScript skills not yet supported: {index_ts}")
        
        return SkillDefinition(
            metadata=metadata,
            description=sections.get('description', ''),
            help=sections.get('help', ''),
            when_to_use=sections.get('when_to_use', []),
            how_to_use=sections.get('how_to_use', ''),
            implementation=sections.get('implementation'),
            edge_cases=sections.get('edge_cases', []),
            skill_type=skill_type,
            executor=executor,
            skill_path=skill_path
        )
    
    @classmethod
    def _parse_metadata(cls, content: str) -> SkillMetadata:
        """Parse YAML front matter metadata"""
        metadata = SkillMetadata(
            name="unknown",
            description=""
        )
        
        front_matter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not front_matter_match:
            return metadata
        
        front_matter = front_matter_match.group(1)
        
        name_match = re.search(r'^name:\s*(.+)$', front_matter, re.MULTILINE)
        if name_match:
            metadata.name = name_match.group(1).strip()
        
        desc_match = re.search(r'^description:\s*(.+)$', front_matter, re.MULTILINE)
        if desc_match:
            metadata.description = desc_match.group(1).strip()
        
        version_match = re.search(r'^version:\s*(.+)$', front_matter, re.MULTILINE)
        if version_match:
            metadata.version = version_match.group(1).strip()
        
        author_match = re.search(r'^author:\s*(.+)$', front_matter, re.MULTILINE)
        if author_match:
            metadata.author = author_match.group(1).strip()
        
        perms_match = re.search(r'^permissions:\s*\[(.+)\]', front_matter, re.MULTILINE)
        if perms_match:
            try:
                perms = json.loads(f"[{perms_match.group(1)}]")
                metadata.permissions = perms
            except:
                pass
        
        tags_match = re.search(r'^tags:\s*\[(.+)\]', front_matter, re.MULTILINE)
        if tags_match:
            try:
                tags = json.loads(f"[{tags_match.group(1)}]")
                metadata.tags = tags
            except:
                pass
        
        requires_match = re.search(r'^requires:\s*\n((?:\s+.+\n?)+)', front_matter, re.MULTILINE)
        if requires_match:
            requires_block = requires_match.group(1)
            metadata.requires = {}
            for line in requires_block.strip().split('\n'):
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    metadata.requires[key.strip()] = value.strip()
        
        metadata_match = re.search(r'metadata:\s*\{([^}]+)\}', front_matter, re.DOTALL)
        if metadata_match:
            try:
                meta_json = '{' + metadata_match.group(1) + '}'
                meta_dict = json.loads(meta_json)
                if 'openclaw' in meta_dict:
                    oc_meta = meta_dict['openclaw']
                    metadata.emoji = oc_meta.get('emoji', '')
                    metadata.os = oc_meta.get('os', [])
                    metadata.primary_env = oc_meta.get('primaryEnv', '')
                    metadata.install = oc_meta.get('install', [])
            except:
                pass
        
        return metadata
    
    @classmethod
    def _parse_sections(cls, content: str) -> Dict[str, Any]:
        """Parse markdown sections"""
        sections = {}
        
        content_without_front = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
        
        section_starts = {}
        for section_name, patterns in cls.SECTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, content_without_front, re.IGNORECASE)
                if match:
                    section_starts[section_name] = match.start()
                    break
        
        sorted_sections = sorted(section_starts.items(), key=lambda x: x[1])
        
        for i, (section_name, start_pos) in enumerate(sorted_sections):
            if i + 1 < len(sorted_sections):
                end_pos = sorted_sections[i + 1][1]
            else:
                end_pos = len(content_without_front)
            
            section_content = content_without_front[start_pos:end_pos]
            
            lines = section_content.split('\n')
            content_lines = []
            for line in lines[1:]:
                if line.startswith('##'):
                    break
                content_lines.append(line)
            
            clean_content = '\n'.join(content_lines).strip()
            
            if section_name in ['when_to_use', 'edge_cases']:
                items = []
                for line in content_lines:
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        items.append(line[2:])
                    elif re.match(r'^\d+\.\s', line):
                        items.append(re.sub(r'^\d+\.\s*', '', line))
                sections[section_name] = items
            else:
                sections[section_name] = clean_content
        
        return sections
    
    @classmethod
    def _load_python_executor(cls, agent_py: Path, skill_name: str) -> Optional[Callable]:
        """Load Python executor from agent.py"""
        try:
            spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", agent_py)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"skill_{skill_name}"] = module
            spec.loader.exec_module(module)
            
            for attr_name in ['execute', 'run', 'main', skill_name.replace('-', '_')]:
                if hasattr(module, attr_name):
                    return getattr(module, attr_name)
            
            return None
        except Exception as e:
            logger.error(f"Error loading executor from {agent_py}: {e}")
            return None


class SkillManager:
    """Manage OpenClaw-compatible skills with three-level progressive disclosure"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, skills_dirs: Optional[List[Path]] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.skills: Dict[str, SkillDefinition] = {}
        self.skills_dirs = skills_dirs or []
        self._watcher = None
        self._watching = False
        self._file_hashes: Dict[str, str] = {}
        
        self._load_priority = [
            'workspace',
            'user', 
            'builtin'
        ]
    
    def add_skills_dir(self, skills_dir: Path) -> None:
        """Add a skills directory"""
        if skills_dir not in self.skills_dirs:
            self.skills_dirs.append(skills_dir)
    
    def load_all_skills(self) -> int:
        """Load all skills from configured directories"""
        loaded = 0
        for skills_dir in self.skills_dirs:
            loaded += self._load_skills_from_dir(skills_dir)
        return loaded
    
    def _load_skills_from_dir(self, skills_dir: Path) -> int:
        """Load skills from a directory"""
        if not skills_dir.exists():
            logger.debug(f"Skills directory does not exist: {skills_dir}")
            return 0
        
        loaded = 0
        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir() and not skill_folder.name.startswith('_'):
                skill = SkillParser.parse_file(skill_folder)
                if skill:
                    self.skills[skill.metadata.name] = skill
                    self._file_hashes[skill.metadata.name] = skill.file_hash
                    loaded += 1
        
        return loaded
    
    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name"""
        return self.skills.get(name)
    
    def list_skills(self) -> List[str]:
        """List all loaded skill names"""
        return list(self.skills.keys())
    
    def get_skill_card(self, name: str) -> Optional[Dict[str, str]]:
        """Get skill card (Level 1: ~24 tokens)"""
        skill = self.skills.get(name)
        if not skill:
            return None
        
        return {
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "emoji": skill.metadata.emoji,
            "location": str(skill.skill_path / "SKILL.md") if skill.skill_path else ""
        }
    
    def get_all_skill_cards(self) -> List[Dict[str, str]]:
        """Get all skill cards for LLM context (Level 1)"""
        return [self.get_skill_card(name) for name in self.skills.keys() if self.get_skill_card(name)]
    
    def get_skill_detail(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill detail (Level 2: full SKILL.md content)"""
        skill = self.skills.get(name)
        if not skill:
            return None
        
        return {
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "when_to_use": skill.when_to_use,
            "how_to_use": skill.how_to_use,
            "edge_cases": skill.edge_cases,
            "permissions": skill.metadata.permissions,
            "requires": skill.metadata.requires
        }
    
    def get_skill_full(self, name: str) -> Optional[SkillDefinition]:
        """Get full skill definition (Level 3: includes executor)"""
        return self.skills.get(name)
    
    def get_skills_prompt(self, level: DisclosureLevel = DisclosureLevel.CARD) -> str:
        """Generate a prompt describing all available skills"""
        if not self.skills:
            return "No skills are currently loaded."
        
        if level == DisclosureLevel.CARD:
            return self._generate_cards_prompt()
        elif level == DisclosureLevel.DETAIL:
            return self._generate_detail_prompt()
        else:
            return self._generate_full_prompt()
    
    def _generate_cards_prompt(self) -> str:
        """Generate Level 1: Card format (~24 tokens per skill)"""
        lines = ["<available_skills>"]
        for skill in self.skills.values():
            emoji = skill.metadata.emoji or "📦"
            lines.append(f'  <skill name="{skill.metadata.name}" emoji="{emoji}">{skill.metadata.description}</skill>')
        lines.append("</available_skills>")
        return '\n'.join(lines)
    
    def _generate_detail_prompt(self) -> str:
        """Generate Level 2: Detail format"""
        parts = ["# Available Skills\n"]
        for skill in self.skills.values():
            parts.append(f"\n## {skill.metadata.name}")
            parts.append(f"Description: {skill.metadata.description}")
            if skill.when_to_use:
                parts.append("When to use:")
                for example in skill.when_to_use[:5]:
                    parts.append(f"  - {example}")
        return '\n'.join(parts)
    
    def _generate_full_prompt(self) -> str:
        """Generate Level 3: Full format"""
        parts = ["# Available Skills (Full)\n"]
        for skill in self.skills.values():
            parts.append(f"\n## {skill.metadata.name}")
            parts.append(f"Description: {skill.metadata.description}")
            parts.append(f"\n{skill.how_to_use}")
            if skill.edge_cases:
                parts.append("\nEdge cases:")
                for case in skill.edge_cases:
                    parts.append(f"  - {case}")
        return '\n'.join(parts)
    
    def get_skill_definitions_for_llm(self) -> List[Dict[str, Any]]:
        """Get skill definitions formatted for LLM"""
        definitions = []
        for skill in self.skills.values():
            definitions.append({
                "name": skill.metadata.name,
                "description": skill.metadata.description,
                "when_to_use": skill.when_to_use,
                "permissions": skill.metadata.permissions
            })
        return definitions
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a skill"""
        skill = self.get_skill(skill_name)
        if not skill:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}"
            }
        
        if skill.skill_type == SkillType.CODE and skill.executor:
            try:
                executor = skill.executor
                if asyncio.iscoroutinefunction(executor):
                    result = await executor(**kwargs)
                else:
                    result = executor(**kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                return {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                logger.error(f"Skill execution error: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": str(e)
                }
        else:
            return {
                "success": True,
                "skill": skill.metadata.name,
                "description": skill.how_to_use,
                "message": "This is a simple skill. The LLM should follow the instructions in the skill definition."
            }
    
    def find_matching_skills(self, user_input: str) -> List[SkillDefinition]:
        """Find skills that match user input"""
        matches = []
        
        # 确保 user_input 是字符串
        if not isinstance(user_input, str):
            user_input = str(user_input)
        
        user_input_lower = user_input.lower()
        
        for skill in self.skills.values():
            for trigger in skill.when_to_use:
                trigger_lower = trigger.lower()
                if any(word in user_input_lower for word in trigger_lower.split() if len(word) > 2):
                    matches.append(skill)
                    break
        
        return matches
    
    def start_hot_reload(self, debounce_ms: int = 250) -> None:
        """Start watching for skill file changes"""
        try:
            from watchfiles import awatch
            
            async def watch_changes():
                self._watching = True
                paths = [str(d) for d in self.skills_dirs if d.exists()]
                if not paths:
                    return
                
                async for changes in awatch(*paths):
                    for change_type, path in changes:
                        if 'SKILL.md' in path:
                            logger.info(f"🔄 检测到 Skill 变更: {path}")
                            self._reload_changed_skill(Path(path))
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(watch_changes())
            else:
                loop.run_until_complete(watch_changes())
                
        except ImportError:
            logger.warning("watchfiles not installed, hot reload disabled. Install with: pip install watchfiles")
    
    def stop_hot_reload(self) -> None:
        """Stop watching for changes"""
        self._watching = False
    
    def _reload_changed_skill(self, skill_md_path: Path) -> bool:
        """Reload a changed skill"""
        skill_dir = skill_md_path.parent
        skill = SkillParser.parse_file(skill_dir)
        if skill:
            old_hash = self._file_hashes.get(skill.metadata.name, "")
            if skill.file_hash != old_hash:
                self.skills[skill.metadata.name] = skill
                self._file_hashes[skill.metadata.name] = skill.file_hash
                logger.info(f"✅ Skill 已热重载: {skill.metadata.name}")
                return True
        return False
    
    def create_skill_from_template(self, name: str, description: str, 
                                    when_to_use: List[str] = None,
                                    how_to_use: str = "",
                                    save_path: Path = None) -> str:
        """Create a new skill from template"""
        template = f'''---
name: {name}
description: {description}
version: "1.0.0"
author: ""
tags: []
---

## Description

{description}

## When to use

'''
        for trigger in (when_to_use or []):
            template += f"- {trigger}\n"
        
        template += f'''
## How to use

{how_to_use or "TODO: Add usage instructions"}

## Edge cases

- TODO: Add edge cases
'''
        
        if save_path:
            skill_dir = save_path / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(template, encoding='utf-8')
            logger.info(f"✅ 创建 Skill: {skill_dir / 'SKILL.md'}")
        
        return template


_skill_manager_instance = None

def get_skill_manager() -> SkillManager:
    """Get the global SkillManager instance"""
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
    return _skill_manager_instance
