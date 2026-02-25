"""
Skills System - OpenClaw Compatible

Features:
- Three-level progressive disclosure (card, detail, full)
- Hot reload support
- AI self-generating skills
- AgentSkills.io standard compatible
"""
from .skill_manager import (
    SkillManager,
    SkillDefinition,
    SkillMetadata,
    SkillParser,
    SkillType,
    DisclosureLevel,
    get_skill_manager
)
from .repository import (
    SkillsRepository,
    SkillInfo,
    skills_repository
)

skill_manager = get_skill_manager()

__all__ = [
    'SkillManager',
    'SkillDefinition', 
    'SkillMetadata',
    'SkillParser',
    'SkillType',
    'DisclosureLevel',
    'get_skill_manager',
    'skill_manager',
    'SkillsRepository',
    'SkillInfo',
    'skills_repository'
]
