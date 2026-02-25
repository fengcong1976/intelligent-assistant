"""
Skill to Agent Generator - 从 OpenClaw Skill 生成 Agent 代码

这个工具可以：
1. 解析 OpenClaw 格式的 Skill 文件
2. 生成 Agent Python 代码框架
3. 保留 Skill 作为意图识别指导
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SkillAction:
    """Skill 中的操作"""
    name: str
    description: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    code_snippet: str = ""


@dataclass
class ParsedSkill:
    """解析后的 Skill"""
    name: str
    description: str = ""
    when_to_use: List[str] = field(default_factory=list)
    actions: List[SkillAction] = field(default_factory=list)
    edge_cases: List[str] = field(default_factory=list)
    raw_content: str = ""


class SkillToAgentGenerator:
    """从 Skill 生成 Agent 代码"""
    
    TEMPLATE = '''"""
{agent_name} - {description}
"""
import asyncio
from typing import Any, Dict, Optional
from loguru import logger

from .base import BaseAgent, Task


class {class_name}(BaseAgent):
    """
    {description}
    
    能力：
{capabilities}
    """

    def __init__(self):
        super().__init__(
            name="{agent_name}",
            description="{short_description}"
        )
        
{register_capabilities}
        
        self._llm_gateway = None
        
        logger.info("{emoji} {agent_name}已初始化")

    def _get_llm_gateway(self):
        """获取 LLM 网关"""
        if self._llm_gateway is None:
            from ..llm import LLMGateway
            from ..config import settings
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway

    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params or {}
        
        logger.info("{emoji} 执行任务: {task_type}")
        
{action_handlers}
        
        else:
            return f"❌ 不支持的操作: {{task_type}}"

{action_methods}
    
    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = super().get_status()
        status.update({{
            # 添加自定义状态
        }})
        return status
'''

    ACTION_HANDLER_TEMPLATE = '''        if task_type == "{action_name}":
            return await self._handle_{action_name}(params)
'''

    ACTION_METHOD_TEMPLATE = '''
    async def _handle_{action_name}(self, params: Dict) -> str:
        """处理 {action_description}"""
        {param_extraction}
        
        # TODO: 实现具体逻辑
        # {code_hint}
        
        return f"✅ {action_description}完成"
'''

    def __init__(self):
        self.emoji_map = {
            "email": "📧",
            "file": "📁",
            "music": "🎵",
            "video": "🎬",
            "weather": "🌤️",
            "news": "📰",
            "contact": "📞",
            "calendar": "📅",
            "search": "🔍",
            "web": "🌐",
            "download": "⬇️",
            "system": "💻",
            "app": "📱",
            "pdf": "📄",
            "code": "👨‍💻",
            "default": "🤖"
        }
    
    def parse_skill(self, skill_path: Path) -> ParsedSkill:
        """解析 Skill 文件"""
        content = skill_path.read_text(encoding='utf-8')
        
        skill = ParsedSkill(
            name=skill_path.stem,
            raw_content=content
        )
        
        lines = content.split('\n')
        current_section = ""
        current_action = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('---'):
                continue
            
            if line.startswith('name:'):
                skill.name = line.split(':', 1)[1].strip()
            elif line.startswith('description:'):
                skill.description = line.split(':', 1)[1].strip()
            elif line.startswith('## When to use'):
                current_section = "when_to_use"
            elif line.startswith('## How to use'):
                current_section = "how_to_use"
            elif line.startswith('## Edge cases'):
                current_section = "edge_cases"
            elif line.startswith('### '):
                if current_section == "how_to_use":
                    if current_action:
                        skill.actions.append(current_action)
                    action_name = line[4:].strip()
                    current_action = SkillAction(name=action_name)
            elif line.startswith('- ') or line.startswith('* '):
                item = line[2:].strip()
                if current_section == "when_to_use":
                    skill.when_to_use.append(item)
                elif current_section == "edge_cases":
                    skill.edge_cases.append(item)
                elif current_section == "how_to_use" and current_action:
                    if ':' in item:
                        key, value = item.split(':', 1)
                        current_action.params[key.strip()] = value.strip()
                    else:
                        current_action.examples.append(item)
            elif line.startswith('```'):
                continue
            elif current_section == "how_to_use" and current_action and line:
                current_action.code_snippet += line + "\n"
        
        if current_action:
            skill.actions.append(current_action)
        
        return skill
    
    def generate_agent_code(self, skill: ParsedSkill) -> str:
        """生成 Agent 代码"""
        agent_name = skill.name
        if not agent_name.endswith('_agent'):
            agent_name = f"{skill.name}_agent"
        
        class_name = ''.join(word.capitalize() for word in agent_name.split('_'))
        
        emoji = self._get_emoji(skill.name)
        
        capabilities = '\n'.join(
            f"    - {action.name}: {action.description or '待实现'}"
            for action in skill.actions
        ) if skill.actions else "    - 待定义"
        
        register_capabilities = '\n'.join(
            f'        self.register_capability("{action.name}")'
            for action in skill.actions
        ) if skill.actions else "        pass"
        
        action_handlers = ''.join(
            self.ACTION_HANDLER_TEMPLATE.format(action_name=action.name.replace('-', '_'))
            for action in skill.actions
        )
        
        action_methods = ''.join(
            self._generate_action_method(action)
            for action in skill.actions
        )
        
        return self.TEMPLATE.format(
            agent_name=agent_name,
            class_name=class_name,
            description=skill.description or f"{skill.name} 智能体",
            short_description=skill.description or f"{skill.name} 智能体",
            capabilities=capabilities,
            register_capabilities=register_capabilities,
            emoji=emoji,
            action_handlers=action_handlers,
            action_methods=action_methods
        )
    
    def _generate_action_method(self, action: SkillAction) -> str:
        """生成操作方法"""
        param_extraction = '\n'.join(
            f'        {key} = params.get("{key}")'
            for key in action.params.keys()
        ) if action.params else "        # 无参数"
        
        code_hint = action.code_snippet[:200] if action.code_snippet else "参考 Skill 文件中的实现"
        
        return self.ACTION_METHOD_TEMPLATE.format(
            action_name=action.name.replace('-', '_'),
            action_description=action.name,
            param_extraction=param_extraction,
            code_hint=code_hint
        )
    
    def _get_emoji(self, name: str) -> str:
        """获取智能体对应的 emoji"""
        name_lower = name.lower()
        for key, emoji in self.emoji_map.items():
            if key in name_lower:
                return emoji
        return self.emoji_map["default"]
    
    def generate_from_file(self, skill_path: Path, output_dir: Path = None) -> str:
        """从 Skill 文件生成 Agent"""
        skill = self.parse_skill(skill_path)
        code = self.generate_agent_code(skill)
        
        if output_dir:
            agent_name = skill.name
            if not agent_name.endswith('_agent'):
                agent_name = f"{skill.name}_agent"
            
            output_path = output_dir / f"{agent_name}.py"
            output_path.write_text(code, encoding='utf-8')
            logger.info(f"✅ 已生成: {output_path}")
        
        return code


def generate_agent_from_skill(skill_path: str, output_dir: str = None) -> str:
    """从 Skill 文件生成 Agent 代码
    
    Args:
        skill_path: Skill 文件路径
        output_dir: 输出目录（可选）
    
    Returns:
        生成的 Agent 代码
    
    Example:
        >>> code = generate_agent_from_skill("skills/send_email/SKILL.md")
        >>> print(code)
    """
    generator = SkillToAgentGenerator()
    skill_file = Path(skill_path)
    output = Path(output_dir) if output_dir else None
    return generator.generate_from_file(skill_file, output)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python skill_to_agent.py <skill_file> [output_dir]")
        sys.exit(1)
    
    skill_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    code = generate_agent_from_skill(skill_file, output_dir)
    print(code)
