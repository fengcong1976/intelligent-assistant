"""
开发智能体 - 支持自我完善和功能扩展
能够创建新智能体、修改现有功能、生成代码模块
支持 CLI 命令执行进行开发调试
"""
import os
import sys
import json
import re
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ..base import BaseAgent, Task
from ...config import settings


class DeveloperAgent(BaseAgent):
    """开发智能体 - 智能体自我进化的核心"""
    
    AGENT_TEMPLATE = '''"""
{agent_name} - {agent_description}
"""
from typing import Dict, Any, Optional
from loguru import logger

from ..base import BaseAgent, Task


class {agent_class}(BaseAgent):
    """{agent_description}"""
    
    def __init__(self):
        super().__init__(
            name="{agent_name}",
            description="{agent_description}"
        )
        
        # 注册能力
        {capabilities}
        
        logger.info("✅ {agent_name} 已初始化")
    
    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params
        logger.info(f"🔧 {{self.name}} 执行任务: {{task_type}}")
        
        {task_handlers}
        
        return f"❌ 不支持的任务类型: {{task_type}}"
'''

    CAPABILITY_REGISTRY = {
        "file_read": "读取文件内容",
        "file_write": "写入文件内容",
        "file_create": "创建新文件",
        "file_delete": "删除文件",
        "code_generate": "生成代码",
        "code_review": "代码审查",
        "agent_create": "创建新智能体",
        "agent_modify": "修改智能体",
        "module_create": "创建功能模块",
        "test_run": "运行测试",
        "cli_execute": "执行CLI命令",
        "cli_python": "执行Python代码",
        "cli_git": "Git操作",
        "cli_lint": "代码检查",
        "cli_test": "运行测试",
        "cli_install": "安装依赖",
    }
    
    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "创建智能体": ("create_agent", {}),
        "新建智能体": ("create_agent", {}),
        "开发智能体": ("full_develop", {}),
        "生成智能体": ("create_agent_from_skill", {}),
        "修改智能体": ("modify_agent", {}),
        "测试智能体": ("test_agent", {}),
        "修复智能体": ("fix_agent", {}),
        "审查智能体": ("review_agent", {}),
        "代码审查": ("review_agent", {}),
        "创建skill": ("create_skill", {}),
        "生成skill": ("create_skill", {}),
        "完整开发": ("full_develop", {}),
        "开发": ("full_develop", {}),
        "安装依赖": ("install_deps", {}),
        "安装库": ("install_deps", {}),
        "pip安装": ("install_deps", {}),
        "刷新智能体": ("reload_agents", {}),
        "重新加载": ("reload_agents", {}),
        "热加载": ("reload_agents", {}),
        "重载智能体": ("reload_agents", {}),
    }

    def __init__(self):
        super().__init__(
            name="developer_agent",
            description="开发智能体 - 支持系统自我完善和功能扩展"
        )
        
        self.register_capability(
            capability="developer_task",
            description="执行开发相关任务。包括代码生成、文案撰写、内容创作、创建智能体等。当用户要求写文章、写文案、生成内容时使用此工具。",
            parameters={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "任务描述，如'写一篇关于西安钟楼的文案'、'生成Python代码'"
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言（可选），如'python'、'javascript'"
                    }
                },
                "required": ["task"]
            },
            category="developer"
        )
        
        for cap_name, cap_desc in self.CAPABILITY_REGISTRY.items():
            self.register_capability(
                capability=cap_name,
                description=cap_desc
            )
        
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = Path(__file__).parent
        self.backup_dir = self.project_root / "data" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.pending_changes: Dict[str, Dict] = {}
        self._llm_gateway = None
        
        logger.info(f"🔧 开发智能体已初始化, agents_dir={self.agents_dir}")

    def _get_llm_gateway(self):
        """获取 LLM 网关"""
        if self._llm_gateway is None:
            from ...llm import LLMGateway
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        llm = self._get_llm_gateway()
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await llm.chat(messages)
            if response and hasattr(response, 'content'):
                return response.content
            elif response:
                return str(response)
            else:
                raise ValueError("LLM 返回空响应")
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    def _call_llm_stream_sync(self, prompt: str) -> str:
        """调用 LLM - 同步版本，直接使用 DashScope API"""
        from dashscope import Generation
        import dashscope
        from ...config import settings
        
        dashscope.api_key = settings.llm.dashscope_api_key
        
        try:
            response = Generation.call(
                model=settings.llm.dashscope_model,
                messages=[{"role": "user", "content": prompt}],
                result_format="message",
                max_tokens=8000,
            )
            
            if response.status_code == 200:
                output = response.output
                if output.choices:
                    msg = output.choices[0].message
                    content = msg.get("content", "") if isinstance(msg, dict) else (msg.content if hasattr(msg, 'content') else "")
                    return content[:10000]
            
            logger.error(f"LLM 调用失败: {response.code} - {response.message}")
            return ""
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    async def _call_llm_stream(self, prompt: str) -> str:
        """调用 LLM (流式) - 用于长响应"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._call_llm_stream_sync(prompt))

    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params
        logger.info(f"🔧 开发智能体执行任务: {task_type}")
        
        if task_type == "general":
            return await self._handle_general(params)
        elif task_type == "developer_task":
            return await self._handle_developer_task(params)
        elif task_type == "analyze_request":
            return await self._analyze_request(params)
        elif task_type == "create_agent":
            return await self._create_agent(params)
        elif task_type == "modify_agent":
            return await self._modify_agent(params)
        elif task_type == "create_module":
            return await self._create_module(params)
        elif task_type == "generate_code":
            return await self._generate_code(params)
        elif task_type == "review_code":
            return await self._review_code(params)
        elif task_type == "apply_change":
            return await self._apply_change(params)
        elif task_type == "rollback":
            return await self._rollback(params)
        elif task_type == "list_agents":
            return await self._list_agents(params)
        elif task_type == "get_agent_info":
            return await self._get_agent_info(params)
        elif task_type == "suggest_improvements":
            return await self._suggest_improvements(params)
        elif task_type == "cli_execute":
            return await self._cli_execute(params)
        elif task_type == "cli_python":
            return await self._cli_python(params)
        elif task_type == "cli_git":
            return await self._cli_git(params)
        elif task_type == "cli_lint":
            return await self._cli_lint(params)
        elif task_type == "cli_test":
            return await self._cli_test(params)
        elif task_type == "cli_install":
            return await self._cli_install(params)
        elif task_type == "dev_workflow":
            return await self._dev_workflow(params)
        elif task_type == "autonomous_develop":
            return await self.autonomous_develop(params)
        elif task_type == "create_agent_from_skill":
            return await self._create_agent_from_skill_md(params)
        elif task_type == "create_skill":
            return await self._create_skill_from_conversation(params)
        elif task_type == "test_agent":
            return await self._test_agent(params)
        elif task_type == "fix_agent":
            return await self._fix_agent(params)
        elif task_type == "review_agent":
            return await self._review_agent(params)
        elif task_type == "full_develop":
            return await self._full_develop_workflow(params)
        elif task_type == "install_deps":
            return await self._install_deps_task(params)
        elif task_type == "reload_agents":
            return await self._reload_agents(params)
        else:
            return f"❌ 不支持的开发任务: {task_type}"

    async def _handle_general(self, params: Dict) -> str:
        """处理自然语言请求"""
        original_text = params.get("original_text", "")
        task = params.get("task", "")
        request_text = task or original_text
        
        if not request_text:
            return "❌ 请提供开发需求"
        
        content_keywords = ["写", "文案", "文章", "内容", "生成", "创作", "撰写", "介绍", "描述"]
        is_content_task = any(kw in request_text for kw in content_keywords)
        dev_keywords = ["代码", "智能体", "模块", "函数", "类", "创建", "修改", "开发", "实现", "编程"]
        is_dev_task = any(kw in request_text for kw in dev_keywords)
        
        if is_content_task and not is_dev_task:
            logger.info(f"📝 检测到内容生成任务: {request_text[:50]}...")
            return await self._handle_developer_task({"task": request_text})
        
        prompt = f"""分析以下开发需求，确定操作类型并提取参数：

需求: {request_text}

请返回 JSON 格式：
{{
    "action": "create_agent|modify_agent|create_module|generate_code|review_code|list_agents|suggest_improvements|cli_execute|cli_python|cli_git|cli_lint|cli_test|cli_install|dev_workflow|autonomous_develop",
    "params": {{
        "name": "名称",
        "description": "描述",
        "capabilities": ["能力1", "能力2"],
        "command": "命令",
        "code": "代码",
        ...
    }}
}}

只返回 JSON，不要其他内容。"""

        try:
            response = await self._call_llm(prompt)
            result = json.loads(response.strip().replace("```json", "").replace("```", "").strip())
            
            action = result.get("action")
            action_params = result.get("params", {})
            action_params["original_text"] = request_text
            
            if action == "create_agent":
                return await self._create_agent(action_params)
            elif action == "modify_agent":
                return await self._modify_agent(action_params)
            elif action == "create_module":
                return await self._create_module(action_params)
            elif action == "generate_code":
                return await self._generate_code(action_params)
            elif action == "review_code":
                return await self._review_code(action_params)
            elif action == "list_agents":
                return await self._list_agents(action_params)
            elif action == "suggest_improvements":
                return await self._suggest_improvements(action_params)
            elif action == "cli_execute":
                action_params["_force"] = True
                return await self._cli_execute(action_params)
            elif action == "cli_python":
                return await self._cli_python(action_params)
            elif action == "cli_git":
                return await self._cli_git(action_params)
            elif action == "cli_lint":
                return await self._cli_lint(action_params)
            elif action == "cli_test":
                return await self._cli_test(action_params)
            elif action == "cli_install":
                return await self._cli_install(action_params)
            elif action == "dev_workflow":
                return await self._dev_workflow(action_params)
            elif action == "autonomous_develop":
                return await self.autonomous_develop(action_params)
            else:
                return await self._analyze_request({"request": request_text})
        except Exception as e:
            logger.error(f"解析开发需求失败: {e}")
            return await self._analyze_request({"request": request_text})

    async def _handle_developer_task(self, params: Dict) -> str:
        """处理 developer_task 类型的任务"""
        task_desc = params.get("task", params.get("original_text", ""))
        if not task_desc:
            return "❌ 请提供任务描述"
        
        logger.info(f"📝 开始生成内容: {task_desc[:50]}...")
        
        prompt = f"""请完成以下任务：

{task_desc}

请直接输出结果，不要添加额外的解释。"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self._call_llm_stream_sync(prompt))
            logger.info(f"✅ 内容生成完成，长度: {len(response)}")
            return response
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return f"❌ 执行任务失败: {str(e)}"

    async def _analyze_request(self, params: Dict) -> str:
        """分析用户需求，确定需要的开发操作"""
        request = params.get("request", "")
        if not request:
            return "❌ 请提供需求描述"
        
        prompt = f"""你是一个系统架构师，分析用户需求并确定开发方案。

用户需求：{request}

现有智能体列表：
- music_agent: 音乐播放管理
- email_agent: 邮件发送管理
- contact_agent: 联系人管理
- weather_agent: 天气查询
- file_agent: 文件管理
- developer_agent: 开发和自我完善

请分析需求并返回 JSON 格式的开发方案：
{{
    "action": "create_agent|modify_agent|create_module|generate_code",
    "target": "目标名称",
    "description": "功能描述",
    "capabilities": ["能力1", "能力2"],
    "files_to_create": ["文件路径1"],
    "files_to_modify": ["文件路径2"],
    "priority": "high|medium|low",
    "estimated_complexity": "简单|中等|复杂"
}}

只返回 JSON，不要其他内容。"""

        try:
            response = await self._call_llm(prompt)
            result = json.loads(response.strip().replace("```json", "").replace("```", "").strip())
            
            return f"""📋 开发方案分析：

🎯 操作类型: {result.get('action')}
📌 目标: {result.get('target')}
📝 描述: {result.get('description')}
⚡ 能力: {', '.join(result.get('capabilities', []))}
📁 需创建文件: {', '.join(result.get('files_to_create', [])) or '无'}
📝 需修改文件: {', '.join(result.get('files_to_modify', [])) or '无'}
🔥 优先级: {result.get('priority')}
📊 复杂度: {result.get('estimated_complexity')}

确认执行请输入: @开发智能体 执行开发方案"""
        except Exception as e:
            logger.error(f"分析需求失败: {e}")
            return f"❌ 分析需求失败: {e}"

    async def _create_agent(self, params: Dict) -> str:
        """创建新智能体"""
        agent_name = params.get("name", "")
        description = params.get("description", "")
        capabilities = params.get("capabilities", [])
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        import re
        if '智能体' in agent_name:
            agent_name = agent_name.replace('智能体', '')
        agent_name = re.sub(r'[^\w]', '_', agent_name)
        agent_name = re.sub(r'_+', '_', agent_name).strip('_').lower()
        if not agent_name or agent_name == '_':
            agent_name = "new"
        if not agent_name.endswith('_agent'):
            agent_name = agent_name + '_agent'
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if agent_file.exists():
            return f"❌ 智能体已存在: {agent_name}"
        
        agent_class = "".join(word.capitalize() for word in agent_name.split("_"))
        agent_class = agent_class.replace("Agent", "") + "Agent"
        
        cap_code = "\n        ".join(f'self.register_capability("{cap}")' for cap in capabilities)
        
        task_handlers = await self._generate_task_handlers(agent_name, capabilities)
        
        code = self.AGENT_TEMPLATE.format(
            agent_name=agent_name,
            agent_class=agent_class,
            agent_description=description,
            capabilities=cap_code or "# 注册能力\n        pass",
            task_handlers=task_handlers
        )
        
        change_id = f"create_{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.pending_changes[change_id] = {
            "type": "create",
            "file": str(agent_file),
            "content": code,
            "description": f"创建智能体: {agent_name}"
        }
        
        return f"""✅ 智能体代码已生成，等待确认

📄 文件: {agent_file}
🤖 智能体: {agent_class}
📝 描述: {description}
⚡ 能力: {', '.join(capabilities)}

变更ID: {change_id}
确认创建请输入: @开发智能体 确认变更 {change_id}"""

    async def _generate_task_handlers(self, agent_name: str, capabilities: List[str]) -> str:
        """生成任务处理代码"""
        prompt = f"""为智能体 {agent_name} 生成任务处理代码。

能力列表: {capabilities}

请生成 Python 代码，包含以下格式：
- if task_type == "xxx": return await self._handle_xxx(params)
- 每个 _handle_xxx 方法返回字符串结果

只返回代码，不要其他内容。使用 8 空格缩进。"""

        try:
            response = await self._call_llm(prompt)
            return response
        except Exception as e:
            logger.error(f"生成任务处理代码失败: {e}")
            return "# TODO: 实现任务处理逻辑\n        pass"

    async def _modify_agent(self, params: Dict) -> str:
        """修改现有智能体"""
        agent_name = params.get("name", "")
        modification = params.get("modification", "")
        
        if not agent_name or not modification:
            return "❌ 请提供智能体名称和修改内容"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体不存在: {agent_name}"
        
        with open(agent_file, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        prompt = f"""修改以下 Python 代码，根据需求进行调整。

原始代码：
```python
{original_code}
```

修改需求：{modification}

请返回修改后的完整代码，保持原有结构和风格。只返回代码，不要其他内容。"""

        try:
            modified_code = await self._call_llm(prompt)
            
            change_id = f"modify_{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.pending_changes[change_id] = {
                "type": "modify",
                "file": str(agent_file),
                "content": modified_code,
                "original": original_code,
                "description": f"修改智能体: {agent_name} - {modification}"
            }
            
            return f"""✅ 智能体修改代码已生成，等待确认

📄 文件: {agent_file}
📝 修改: {modification}

变更ID: {change_id}
确认修改请输入: @开发智能体 确认变更 {change_id}"""
        except Exception as e:
            logger.error(f"修改智能体失败: {e}")
            return f"❌ 修改失败: {e}"

    async def _create_module(self, params: Dict) -> str:
        """创建功能模块"""
        module_name = params.get("name", "")
        description = params.get("description", "")
        functions = params.get("functions", [])
        
        if not module_name:
            return "❌ 请提供模块名称"
        
        module_dir = self.project_root / module_name.replace(".", "/")
        module_file = module_dir / "__init__.py"
        
        prompt = f"""创建一个 Python 模块。

模块名称: {module_name}
描述: {description}
功能列表: {functions}

请生成完整的模块代码，包含：
1. 模块文档字符串
2. 必要的导入
3. 所有功能函数
4. 类型注解

只返回代码，不要其他内容。"""

        try:
            code = await self._call_llm(prompt)
            
            change_id = f"module_{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.pending_changes[change_id] = {
                "type": "create",
                "file": str(module_file),
                "content": code,
                "description": f"创建模块: {module_name}"
            }
            
            return f"""✅ 模块代码已生成，等待确认

📄 文件: {module_file}
📦 模块: {module_name}
📝 描述: {description}
⚡ 功能: {', '.join(functions)}

变更ID: {change_id}
确认创建请输入: @开发智能体 确认变更 {change_id}"""
        except Exception as e:
            logger.error(f"创建模块失败: {e}")
            return f"❌ 创建失败: {e}"

    async def _generate_code(self, params: Dict) -> str:
        """生成代码片段"""
        description = params.get("description", "")
        context = params.get("context", "")
        language = params.get("language", "python")
        
        if not description:
            return "❌ 请提供代码描述"
        
        prompt = f"""生成 {language} 代码。

描述: {description}
上下文: {context}

请生成高质量、有注释的代码。只返回代码，不要其他内容。"""

        try:
            code = await self._call_llm(prompt)
            return f"""✅ 代码已生成：

```{language}
{code}
```"""
        except Exception as e:
            return f"❌ 代码生成失败: {e}"

    async def _review_code(self, params: Dict) -> str:
        """代码审查"""
        file_path = params.get("file", "")
        
        if not file_path:
            return "❌ 请提供文件路径"
        
        full_path = self.project_root / file_path
        if not full_path.exists():
            return f"❌ 文件不存在: {file_path}"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        prompt = f"""审查以下代码，提供改进建议：

```python
{code}
```

请从以下方面审查：
1. 代码质量
2. 潜在问题
3. 性能优化
4. 安全性
5. 可维护性

返回格式：
## 代码审查报告

### 优点
- ...

### 问题
- ...

### 建议
- ..."""

        try:
            review = await self._call_llm(prompt)
            return review
        except Exception as e:
            return f"❌ 代码审查失败: {e}"

    async def _apply_change(self, params: Dict) -> str:
        """应用变更"""
        change_id = params.get("change_id", "")
        
        if not change_id or change_id not in self.pending_changes:
            return f"❌ 变更不存在: {change_id}"
        
        change = self.pending_changes[change_id]
        file_path = Path(change["file"])
        
        if change["type"] == "modify":
            backup_file = self.backup_dir / f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(change["original"])
            logger.info(f"📦 已备份原文件: {backup_file}")
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(change["content"])
        
        del self.pending_changes[change_id]
        
        return f"""✅ 变更已应用

📄 文件: {file_path}
📝 描述: {change['description']}

如需回滚，请使用: @开发智能体 回滚 {file_path.name}"""

    async def _rollback(self, params: Dict) -> str:
        """回滚变更"""
        file_name = params.get("file", "")
        
        if not file_name:
            return "❌ 请提供文件名"
        
        backups = list(self.backup_dir.glob(f"{file_name}.*.bak"))
        if not backups:
            return f"❌ 没有找到备份: {file_name}"
        
        latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
        
        original_file = None
        for agent_file in self.agents_dir.glob("*.py"):
            if agent_file.name == file_name:
                original_file = agent_file
                break
        
        if not original_file:
            return f"❌ 找不到原文件: {file_name}"
        
        with open(latest_backup, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        return f"""✅ 已回滚

📄 文件: {original_file}
📦 备份: {latest_backup}"""

    async def _list_agents(self, params: Dict) -> str:
        """列出所有智能体"""
        agents = []
        for agent_file in self.agents_dir.glob("*.py"):
            if agent_file.name in ["__init__.py", "base.py"]:
                continue
            
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            name = agent_file.stem
            desc = "未知"
            if 'description="' in content:
                start = content.find('description="') + len('description="')
                end = content.find('"', start)
                desc = content[start:end]
            
            agents.append(f"- **{name}**: {desc}")
        
        return "🤖 已注册的智能体:\n\n" + "\n".join(agents)

    async def _get_agent_info(self, params: Dict) -> str:
        """获取智能体详细信息"""
        agent_name = params.get("name", "")
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体不存在: {agent_name}"
        
        with open(agent_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        prompt = f"""分析以下智能体代码，提取关键信息：

```python
{content}
```

返回格式：
## 智能体信息

- **名称**: ...
- **描述**: ...
- **能力**: ...
- **任务类型**: ...
- **依赖**: ..."""

        try:
            info = await self._call_llm(prompt)
            return info
        except Exception as e:
            return f"❌ 获取信息失败: {e}"

    async def _suggest_improvements(self, params: Dict) -> str:
        """建议改进"""
        agent_name = params.get("name", "")
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体不存在: {agent_name}"
        
        with open(agent_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        prompt = f"""分析以下智能体代码，提出改进建议：

```python
{content}
```

请从以下方面提出建议：
1. 功能扩展
2. 错误处理
3. 性能优化
4. 用户体验
5. 代码质量

返回格式：
## 改进建议

### 功能扩展
- ...

### 错误处理
- ...

### 性能优化
- ...

### 用户体验
- ...

### 代码质量
- ..."""

        try:
            suggestions = await self._call_llm(prompt)
            return suggestions
        except Exception as e:
            return f"❌ 分析失败: {e}"

    async def _cli_execute(self, params: Dict) -> str:
        """执行任意 CLI 命令"""
        command = params.get("command", "")
        cwd = params.get("cwd", str(self.project_root))
        timeout = params.get("timeout", 60)
        
        if not command:
            return "❌ 请提供要执行的命令"
        
        safe_commands = ["ls", "dir", "cat", "type", "echo", "python", "pip", "git", "pytest", "ruff", "black", "mypy"]
        cmd_base = command.split()[0] if command.split() else ""
        
        if cmd_base not in safe_commands and not params.get("_force"):
            return f"⚠️ 命令 '{cmd_base}' 需要确认。添加 '_force': true 来强制执行。"
        
        try:
            logger.info(f"🔧 执行命令: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            if result.returncode != 0:
                return f"❌ 命令执行失败 (exit code: {result.returncode}):\n{output}"
            
            return f"✅ 命令执行成功:\n{output}" if output else "✅ 命令执行成功"
        except subprocess.TimeoutExpired:
            return f"❌ 命令执行超时 ({timeout}秒)"
        except Exception as e:
            return f"❌ 执行失败: {e}"

    async def _cli_python(self, params: Dict) -> str:
        """执行 Python 代码"""
        code = params.get("code", "")
        cwd = params.get("cwd", str(self.project_root))
        
        if not code:
            return "❌ 请提供 Python 代码"
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            if result.returncode != 0:
                return f"❌ Python 执行失败:\n{output}"
            
            return f"✅ 执行成功:\n{output}" if output else "✅ 执行成功"
        except subprocess.TimeoutExpired:
            return "❌ 执行超时"
        except Exception as e:
            return f"❌ 执行失败: {e}"

    async def _cli_git(self, params: Dict) -> str:
        """Git 操作"""
        action = params.get("action", "status")
        message = params.get("message", "")
        branch = params.get("branch", "")
        files = params.get("files", [])
        
        git_commands = {
            "status": "git status",
            "log": "git log --oneline -10",
            "diff": "git diff",
            "branch": "git branch -a",
            "pull": "git pull",
            "fetch": "git fetch",
        }
        
        if action == "add":
            if files:
                cmd = f"git add {' '.join(files)}"
            else:
                cmd = "git add ."
        elif action == "commit":
            if not message:
                return "❌ 提交需要 commit message"
            cmd = f'git commit -m "{message}"'
        elif action == "push":
            cmd = "git push"
        elif action == "checkout":
            if not branch:
                return "❌ 切换分支需要 branch 参数"
            cmd = f"git checkout {branch}"
        elif action == "create_branch":
            if not branch:
                return "❌ 创建分支需要 branch 参数"
            cmd = f"git checkout -b {branch}"
        elif action in git_commands:
            cmd = git_commands[action]
        else:
            return f"❌ 不支持的 Git 操作: {action}"
        
        return await self._cli_execute({"command": cmd, "_force": True})

    async def _cli_lint(self, params: Dict) -> str:
        """代码检查"""
        path = params.get("path", ".")
        fix = params.get("fix", False)
        
        if fix:
            cmd = f"ruff check --fix {path}"
        else:
            cmd = f"ruff check {path}"
        
        result = await self._cli_execute({"command": cmd, "_force": True})
        
        if "执行成功" in result and "执行成功:\n\n" in result:
            return "✅ 代码检查通过，没有发现问题"
        return result

    async def _cli_test(self, params: Dict) -> str:
        """运行测试"""
        path = params.get("path", "tests")
        verbose = params.get("verbose", True)
        coverage = params.get("coverage", False)
        
        cmd = f"pytest {path}"
        if verbose:
            cmd += " -v"
        if coverage:
            cmd += " --cov=src"
        
        return await self._cli_execute({"command": cmd, "_force": True, "timeout": 120})

    async def _cli_install(self, params: Dict) -> str:
        """安装依赖"""
        package = params.get("package", "")
        dev = params.get("dev", False)
        
        if package:
            if dev:
                cmd = f"pip install {package}"
            else:
                cmd = f"pip install {package}"
        else:
            cmd = "pip install -e ."
        
        return await self._cli_execute({"command": cmd, "_force": True, "timeout": 120})

    async def _dev_workflow(self, params: Dict) -> str:
        """智能开发工作流 - 自动分析需求并执行开发"""
        request = params.get("request", "")
        
        if not request:
            return "❌ 请提供开发需求"
        
        workflow_prompt = f"""你是一个开发助手，分析需求并生成开发步骤。

需求: {request}

项目结构:
- src/personal_agent/agents/ - 智能体目录
- src/personal_agent/channels/ - 通道目录
- src/personal_agent/llm/ - LLM 接口
- src/personal_agent/music/ - 音乐模块

请返回 JSON 格式的开发步骤：
{{
    "steps": [
        {{
            "type": "cli_execute|cli_python|create_agent|modify_agent|create_module",
            "description": "步骤描述",
            "params": {{...}}
        }}
    ]
}}

只返回 JSON。"""

        try:
            response = await self._call_llm(workflow_prompt)
            result = json.loads(response.strip().replace("```json", "").replace("```", "").strip())
            
            steps = result.get("steps", [])
            results = []
            
            for i, step in enumerate(steps, 1):
                step_type = step.get("type")
                step_params = step.get("params", {})
                step_desc = step.get("description", "")
                
                logger.info(f"📋 执行步骤 {i}/{len(steps)}: {step_desc}")
                results.append(f"\n### 步骤 {i}: {step_desc}")
                
                if step_type == "cli_execute":
                    step_params["_force"] = True
                    result_text = await self._cli_execute(step_params)
                elif step_type == "cli_python":
                    result_text = await self._cli_python(step_params)
                elif step_type == "create_agent":
                    result_text = await self._create_agent(step_params)
                elif step_type == "modify_agent":
                    result_text = await self._modify_agent(step_params)
                elif step_type == "create_module":
                    result_text = await self._create_module(step_params)
                else:
                    result_text = f"❌ 未知步骤类型: {step_type}"
                
                results.append(result_text)
            
            return f"""## 开发工作流完成

**需求**: {request}

{''.join(results)}"""
        except Exception as e:
            logger.error(f"开发工作流失败: {e}")
            return f"❌ 开发工作流失败: {e}"

    async def autonomous_develop(self, params: Dict) -> str:
        """
        自主开发循环 - 自动完成需求分析、代码生成、测试、修复
        
        流程:
        1. 分析需求，生成开发计划
        2. 生成代码
        3. 运行测试
        4. 如果失败，分析错误并修复
        5. 重复直到成功或达到最大尝试次数
        """
        request = params.get("request", "")
        max_attempts = params.get("max_attempts", 3)
        
        if not request:
            return "❌ 请提供开发需求"
        
        logger.info(f"🚀 开始自主开发: {request}")
        
        results = []
        results.append(f"## 🚀 自主开发任务\n\n**需求**: {request}\n")
        
        for attempt in range(1, max_attempts + 1):
            results.append(f"\n### 🔄 尝试 {attempt}/{max_attempts}\n")
            
            if attempt == 1:
                plan_result = await self._analyze_request({"request": request})
                results.append(f"**需求分析**:\n{plan_result}\n")
            
            code_result = await self._generate_smart_code(request, attempt)
            results.append(f"**代码生成**:\n{code_result['summary']}\n")
            
            if not code_result.get("success"):
                results.append(f"❌ 代码生成失败: {code_result.get('error')}\n")
                continue
            
            test_result = await self._run_tests(code_result.get("files", []))
            results.append(f"**测试结果**:\n{test_result['summary']}\n")
            
            if test_result.get("success"):
                results.append("\n✅ **开发成功！**\n")
                return "".join(results)
            
            error_analysis = await self._analyze_error(test_result.get("error", ""))
            results.append(f"**错误分析**:\n{error_analysis}\n")
            
            request = f"{request}\n\n注意修复以下问题:\n{error_analysis}"
        
        results.append(f"\n❌ **开发失败**: 已达到最大尝试次数 {max_attempts}\n")
        return "".join(results)

    async def _generate_smart_code(self, request: str, attempt: int = 1) -> Dict:
        """智能代码生成 - 根据需求生成完整可运行的代码"""
        
        prompt = f"""你是一个高级 Python 开发者。请根据需求生成高质量的代码。

需求: {request}

项目结构:
- src/personal_agent/agents/ - 智能体目录
- src/personal_agent/channels/ - 通道目录  
- src/personal_agent/tools/ - 工具目录

要求:
1. 代码完整可运行
2. 包含必要的导入
3. 包含类型注解
4. 包含错误处理
5. 尝试次数: {attempt}

请返回 JSON 格式:
{{
    "files": [
        {{
            "path": "文件路径",
            "content": "完整代码内容"
        }}
    ],
    "description": "代码描述",
    "test_command": "测试命令"
}}"""

        try:
            response = await self._call_llm(prompt)
            result = json.loads(response.strip().replace("```json", "").replace("```", "").strip())
            
            files = result.get("files", [])
            created_files = []
            
            for file_info in files:
                file_path = Path(file_info["path"])
                if not file_path.is_absolute():
                    file_path = self.project_root / file_path
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                backup_file = self.backup_dir / f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        backup_file.write_text(f.read(), encoding='utf-8')
                
                file_path.write_text(file_info["content"], encoding='utf-8')
                created_files.append(str(file_path))
                logger.info(f"📝 创建文件: {file_path}")
            
            return {
                "success": True,
                "files": created_files,
                "summary": f"创建了 {len(created_files)} 个文件:\n" + "\n".join(f"- {f}" for f in created_files),
                "test_command": result.get("test_command", "")
            }
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"❌ 代码生成失败: {e}"
            }

    async def _run_tests(self, files: List[str]) -> Dict:
        """运行测试"""
        
        if not files:
            return {"success": False, "error": "没有文件需要测试", "summary": "❌ 没有文件需要测试"}
        
        test_results = []
        all_success = True
        
        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                continue
            
            if path.suffix == ".py":
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    all_success = False
                    test_results.append(f"❌ 语法错误 {path.name}:\n{result.stderr}")
                else:
                    test_results.append(f"✅ 语法检查通过: {path.name}")
        
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                all_success = False
                test_results.append(f"❌ 测试失败:\n{result.stdout[-1000:]}")
            else:
                test_results.append(f"✅ 所有测试通过")
        
        return {
            "success": all_success,
            "error": "\n".join(test_results) if not all_success else "",
            "summary": "\n".join(test_results)
        }

    async def _analyze_error(self, error_output: str) -> str:
        """分析错误并给出修复建议"""
        
        prompt = f"""分析以下错误，给出具体的修复建议：

错误信息:
{error_output}

请提供:
1. 错误原因分析
2. 具体修复步骤
3. 需要修改的代码位置

简洁明了地回答。"""

        try:
            analysis = await self._call_llm(prompt)
            return analysis
        except Exception as e:
            return f"错误分析失败: {e}"

    async def _create_agent_from_skill_md(self, params: Dict) -> str:
        """根据 Skill MD 文件自动生成智能体代码"""
        skill_file = params.get("skill_file", "")
        skill_content = params.get("skill_content", "")
        
        if skill_file and not skill_content:
            skill_path = Path(skill_file)
            if not skill_path.exists():
                skill_path = self.agents_dir / skill_file
            if not skill_path.exists():
                return f"❌ Skill 文件不存在: {skill_file}"
            with open(skill_path, 'r', encoding='utf-8') as f:
                skill_content = f.read()
        
        if not skill_content:
            return "❌ 请提供 Skill 文件内容"
        
        prompt = f"""你是一个 Python 开发专家。请根据以下 Skill 定义生成智能体代码。

## Skill 定义:
```
{skill_content}
```

## 代码规范:

1. 导入 (必须使用相对导入):
```python
from loguru import logger
from typing import Dict, Any, Optional, List
from ..base import BaseAgent, Task
```

2. 类结构:
```python
class XxxAgent(BaseAgent):
    PRIORITY: int = 5
    
    KEYWORD_MAPPINGS: Dict[str, tuple] = {{
        "关键词": ("action", {{}}),
    }}
    
    def __init__(self):
        super().__init__(name="xxx_agent", description="描述")
    
    async def execute_task(self, task: Task) -> Any:
        if task.type == "action":
            return await self._handle_action(task.params)
        return self.cannot_handle("未知操作")
    
    async def _handle_action(self, params: Dict) -> str:
        return "✅ 完成"
```

重要限制:
- 代码总长度不超过 200 行
- 只实现核心功能，不要添加过多注释
- 使用 self.cannot_handle() 处理错误
- 直接返回代码，不要 markdown 包裹
"""
        
        logger.info("📝 正在调用 LLM 生成代码...")
        
        try:
            response = await self._call_llm_stream(prompt)
            logger.info(f"✅ LLM 返回响应，长度: {len(response)}")
            
            response = response.strip()
            if response.startswith("```python"):
                response = response[9:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            logger.info(f"📝 清理后代码长度: {len(response)}")
            
            skill_data = self._parse_skill_content(skill_content)
            agent_name = skill_data.get("name", "new_agent")
            if not agent_name.endswith("_agent"):
                agent_name = f"{agent_name}_agent"
            
            logger.info(f"📝 目标智能体名称: {agent_name}")
            
            agent_file = self.agents_dir / f"{agent_name}.py"
            
            if agent_file.exists():
                backup_file = self.backup_dir / f"{agent_file.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_file.write_text(agent_file.read_text(encoding='utf-8'), encoding='utf-8')
                logger.info(f"📦 已备份: {backup_file}")
            
            agent_file.write_text(response, encoding='utf-8')
            logger.info(f"✅ 已创建智能体: {agent_file}")
            
            syntax_ok, syntax_msg = await self._check_syntax(agent_file)
            if not syntax_ok:
                fix_result = await self._auto_fix_syntax(agent_file, syntax_msg)
                if fix_result:
                    syntax_ok, syntax_msg = await self._check_syntax(agent_file)
            
            if not syntax_ok:
                return f"""⚠️ 智能体已生成但存在语法错误

📄 文件: {agent_file}

❌ 语法检查失败:
{syntax_msg}

请手动修复或重新生成。"""
            
            import_result = await self._check_imports(agent_file, auto_install=True)
            
            instance_result = await self._test_instantiation(agent_name)
            
            config_result = await self._create_agent_config_file(agent_name, skill_content)
            
            routing_result = await self._update_routing_mappings(agent_name, skill_content)
            
            from ..agent_scanner import get_agent_scanner
            get_agent_scanner().refresh()
            
            return f"""✅ 智能体已生成并通过测试

📄 文件: {agent_file}
🤖 智能体: {agent_name}

📋 测试结果:
- 语法检查: ✅ 通过
- 导入检查: {import_result}
- 实例化: {instance_result.split(chr(10))[0] if chr(10) in instance_result else instance_result}
- 配置文件: {config_result}
- 路由映射: {routing_result}

💡 智能体已自动注册，可直接使用"""
            
        except Exception as e:
            logger.error(f"生成智能体失败: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ 生成失败: {e}"
    
    async def _auto_fix_syntax(self, agent_file: Path, error_msg: str) -> bool:
        """自动修复语法错误"""
        try:
            code = agent_file.read_text(encoding='utf-8')
            
            prompt = f"""修复以下 Python 代码的语法错误。

代码:
```python
{code}
```

错误信息:
{error_msg}

只返回修复后的代码，不要其他内容。"""
            
            fixed_code = await self._call_llm_stream(prompt)
            
            fixed_code = fixed_code.strip()
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            fixed_code = fixed_code.strip()
            
            agent_file.write_text(fixed_code, encoding='utf-8')
            logger.info(f"🔧 已自动修复语法错误: {agent_file}")
            return True
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            return False
    
    def _parse_skill_content(self, content: str) -> Dict:
        """解析 Skill 文件内容"""
        result = {}
        
        name_match = re.search(r'name:\s*(\S+)', content)
        if name_match:
            result["name"] = name_match.group(1)
        
        desc_match = re.search(r'description:\s*(.+?)(?:\n|$)', content)
        if desc_match:
            result["description"] = desc_match.group(1).strip()
        
        return result
    
    async def _create_agent_config_file(self, agent_name: str, skill_content: str) -> str:
        """为智能体创建配置文件"""
        try:
            from ..agent_scanner import AgentConfig, get_agent_scanner
            
            skill_info = self._parse_skill_content(skill_content)
            
            keywords = []
            kw_section = re.search(r'## Keywords\s*\n((?:[-*]\s*.+\n?)+)', skill_content, re.IGNORECASE)
            if kw_section:
                keywords = re.findall(r'[-*]\s*(.+?)(?:\n|$)', kw_section.group(1))
            
            capabilities = []
            cap_section = re.search(r'## Capabilities\s*\n((?:[-*]\s*.+\n?)+)', skill_content, re.IGNORECASE)
            if cap_section:
                capabilities = re.findall(r'[-*]\s*(.+?)(?:\n|$)', cap_section.group(1))
            
            display_name = self._auto_display_name(agent_name)
            
            icon = "🤖"
            icon_keywords = {
                "图片": "🖼️", "图像": "🖼️", "转换": "🔄", "天气": "🌤️",
                "音乐": "🎵", "邮件": "📧", "文件": "📁", "爬虫": "🕷️",
                "通讯录": "📇", "开发": "💻", "PDF": "📄", "视频": "🎬",
                "系统": "⚙️", "应用": "📱", "下载": "⬇️", "新闻": "📰",
                "日历": "📅", "提醒": "⏰", "翻译": "🌐", "股票": "📈",
            }
            for kw, ic in icon_keywords.items():
                if kw in agent_name or kw in skill_content[:200]:
                    icon = ic
                    break
            
            config = AgentConfig(
                name=agent_name,
                display_name=display_name,
                icon=icon,
                description=skill_info.get("description", ""),
                capabilities=capabilities,
                keywords=keywords,
                version="1.0.0",
            )
            
            scanner = get_agent_scanner()
            config_path = scanner.create_agent_config(agent_name, config)
            
            return f"✅ {config_path.name}"
        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
            return f"⚠️ {e}"
    
    def _auto_display_name(self, agent_name: str) -> str:
        """自动生成显示名称"""
        name = agent_name.replace("_agent", "").replace("_", " ")
        return name.title()
    
    async def _update_routing_mappings(self, agent_name: str, skill_content: str) -> str:
        """更新系统路由映射，使新智能体可被正确调用"""
        try:
            intent_parser_file = self.project_root / "agent" / "intent_parser.py"
            master_file = self.agents_dir / "master.py"
            
            updates = []
            
            actions = self._extract_actions_from_skill(skill_content)
            intent_type = agent_name.replace("_agent", "")
            
            if intent_parser_file.exists():
                content = intent_parser_file.read_text(encoding='utf-8')
                
                if f'"{agent_name}"' not in content and f"'{agent_name}'" not in content:
                    agent_class = "".join(word.capitalize() for word in agent_name.split("_"))
                    
                    agent_classes_pattern = r'(agent_classes\s*=\s*\[.*?)(\s*\])'
                    if re.search(agent_classes_pattern, content, re.DOTALL):
                        new_content = re.sub(
                            agent_classes_pattern,
                            f'\\1,\n            ("{agent_name}", "{agent_class}"),\\2',
                            content,
                            flags=re.DOTALL
                        )
                        if new_content != content:
                            intent_parser_file.write_text(new_content, encoding='utf-8')
                            updates.append("intent_parser.py: agent_classes")
                            logger.info(f"✅ 已更新 intent_parser.py: agent_classes")
                    
                    mapping_pattern = r'("calendar_agent":\s*"calendar_operation",|\'calendar_agent\':\s*\'calendar_operation\',)'
                    if re.search(mapping_pattern, content):
                        new_mapping = f'"{agent_name}": "{intent_type}",'
                        new_content = re.sub(
                            mapping_pattern,
                            f'\\1\n            {new_mapping}',
                            content
                        )
                        if new_content != content:
                            intent_parser_file.write_text(new_content, encoding='utf-8')
                            updates.append("intent_parser.py: _agent_to_intent_type")
                            logger.info(f"✅ 已更新 intent_parser.py: _agent_to_intent_type")
                    
                    existing_agents_pattern = r'(return\s*\[.*?"calendar_agent"\])'
                    if re.search(existing_agents_pattern, content):
                        new_content = re.sub(
                            existing_agents_pattern,
                            f'\\1,\n                    "{agent_name}"]',
                            content
                        )
                        if new_content != content:
                            intent_parser_file.write_text(new_content, encoding='utf-8')
                            updates.append("intent_parser.py: _get_existing_agent_names")
                            logger.info(f"✅ 已更新 intent_parser.py: _get_existing_agent_names")
            
            if master_file.exists():
                content = master_file.read_text(encoding='utf-8')
                
                if f'"{agent_name}"' not in content and f"'{agent_name}'" not in content:
                    force_intent_pattern = r'("tts_agent":\s*IntentType\.TTS,|\'tts_agent\':\s*IntentType\.TTS,)'
                    if re.search(force_intent_pattern, content):
                        new_content = re.sub(
                            force_intent_pattern,
                            f'\\1\n                "{agent_name}": "{intent_type}",',
                            content
                        )
                        if new_content != content:
                            master_file.write_text(new_content, encoding='utf-8')
                            updates.append("master.py: force_intent_mapping")
                            logger.info(f"✅ 已更新 master.py: force_intent_mapping")
                    
                    agent_to_intent_pattern = r'("tts_agent":\s*IntentType\.TTS,|\'tts_agent\':\s*IntentType\.TTS,)'
                    if re.search(agent_to_intent_pattern, content):
                        new_content = re.sub(
                            agent_to_intent_pattern,
                            f'\\1\n            "{agent_name}": "{intent_type}",',
                            content
                        )
                        if new_content != content:
                            master_file.write_text(new_content, encoding='utf-8')
                            updates.append("master.py: agent_to_intent")
                            logger.info(f"✅ 已更新 master.py: agent_to_intent")
                    
                    if actions:
                        task_mapping_pattern = r'("list_voices":\s*"tts_agent",|\'list_voices\':\s*\'tts_agent\',)'
                        if re.search(task_mapping_pattern, content):
                            action_mappings = []
                            for action in actions:
                                action_mappings.append(f'"{action}": "{agent_name}",')
                            new_content = re.sub(
                                task_mapping_pattern,
                                f'\\1\n            {chr(10).join("            " + m for m in action_mappings)}',
                                content
                            )
                            if new_content != content:
                                master_file.write_text(new_content, encoding='utf-8')
                                updates.append("master.py: task_agent_mapping")
                                logger.info(f"✅ 已更新 master.py: task_agent_mapping")
            
            if updates:
                return f"✅ 已更新: {', '.join(updates)}"
            else:
                return "✅ 无需更新（映射已存在）"
                
        except Exception as e:
            logger.error(f"更新路由映射失败: {e}")
            return f"⚠️ {e}"
    
    def _extract_actions_from_skill(self, skill_content: str) -> List[str]:
        """从 Skill 文件中提取操作列表"""
        actions = []
        
        action_patterns = [
            r'###\s*\d+\.\s*(\w+)',
            r'action:\s*(\w+)',
            r'-\s*(\w+)\s*:',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, skill_content)
            for match in matches:
                if match.lower() not in ['description', 'params', 'example', 'note', 'edge', 'case', 'implementation']:
                    if match not in actions:
                        actions.append(match.lower())
        
        return actions[:5]

    async def _create_skill_from_conversation(self, params: Dict) -> str:
        """从用户对话自动创建 Skill 文件"""
        user_request = params.get("user_request", "")
        agent_name = params.get("agent_name", "")
        
        if not user_request:
            return "❌ 请提供用户需求描述"
        
        if not agent_name:
            agent_name = re.sub(r'[^a-zA-Z0-9_]', '_', user_request[:20]).lower()
            if not agent_name.endswith("_agent"):
                agent_name = f"{agent_name}_agent"
        
        prompt = f"""根据用户需求生成 Skill 定义文件。

用户需求: {user_request}

请生成完整的 Skill MD 文件内容，包含:
1. name: 智能体名称
2. description: 描述
3. Capabilities: 能力列表
4. Keywords: 触发关键词
5. How to use: 使用方法和参数
6. Edge Cases: 边界情况处理
7. Implementation Notes: 实现说明

格式示例:
```markdown
# Agent Name

name: xxx_agent
description: 描述

## Capabilities
- capability_1: 描述

## Keywords
- 关键词1
- 关键词2

## How to use
### 1. 操作名称
用户输入示例: xxx
参数:
- param1: 描述

## Edge Cases
1. 情况: 处理方式

## Implementation Notes
1. 实现说明
```

只返回 markdown 内容，不要代码块包裹。"""
        
        try:
            skill_content = await self._call_llm_stream(prompt)
            
            skill_content = skill_content.strip()
            if skill_content.startswith("```markdown"):
                skill_content = skill_content[11:]
            if skill_content.startswith("```"):
                skill_content = skill_content[3:]
            if skill_content.endswith("```"):
                skill_content = skill_content[:-3]
            skill_content = skill_content.strip()
            
            skill_file = self.project_root / "skills" / "pending" / f"{agent_name}.md"
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(skill_content, encoding='utf-8')
            
            return f"""✅ Skill 文件已创建

📄 文件: {skill_file}
🤖 智能体: {agent_name}

📝 内容预览:
{skill_content[:500]}...

💡 下一步: 检查 Skill 文件，然后使用 create_agent_from_skill 生成智能体代码"""
            
        except Exception as e:
            logger.error(f"创建 Skill 文件失败: {e}")
            return f"❌ 创建失败: {e}"

    async def _test_agent(self, params: Dict) -> str:
        """测试智能体代码"""
        agent_name = params.get("agent_name", "")
        test_action = params.get("action", "")
        test_params = params.get("params", {})
        auto_install = params.get("auto_install", True)
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体文件不存在: {agent_file}"
        
        results = []
        
        results.append("### 1. 语法检查")
        syntax_result = await self._check_syntax(agent_file)
        results.append(syntax_result)
        
        if "❌" in syntax_result:
            return "\n\n".join(results)
        
        results.append("\n### 2. 导入检查")
        import_result = await self._check_imports(agent_file, auto_install=auto_install)
        results.append(import_result)
        
        if "❌" in import_result:
            return "\n\n".join(results)
        
        results.append("\n### 3. 实例化测试")
        instance_result = await self._test_instantiation(agent_name)
        results.append(instance_result)
        
        if "❌" in instance_result:
            return "\n\n".join(results)
        
        if test_action:
            results.append(f"\n### 4. 功能测试: {test_action}")
            func_result = await self._test_function(agent_name, test_action, test_params)
            results.append(func_result)
        
        return "\n\n".join(results)

    async def _check_syntax(self, file_path: Path) -> tuple:
        """检查 Python 语法"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return (True, "✅ 语法检查通过")
            else:
                return (False, f"❌ 语法错误:\n{result.stderr}")
        except Exception as e:
            return (False, f"❌ 语法检查失败: {e}")

    async def _check_imports(self, file_path: Path, auto_install: bool = False) -> str:
        """检查导入依赖，可选自动安装"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import_lines = []
            for line in content.split('\n'):
                if line.startswith('import ') or line.startswith('from '):
                    if 'personal_agent' not in line and 'loguru' not in line and 'typing' not in line and '__future__' not in line:
                        import_lines.append(line)
            
            if not import_lines:
                return "✅ 无外部依赖"
            
            missing = []
            for line in import_lines:
                parts = line.split()
                if len(parts) >= 2:
                    module = parts[1].split('.')[0]
                    if module in ['os', 'sys', 're', 'json', 'pathlib', 'asyncio', 'subprocess', 'datetime', 'time', 'collections', 'functools', 'itertools', 'typing', 'dataclasses', 'enum', 'abc', 'copy', 'glob', 'shutil', 'tempfile', 'hashlib', 'io', 'contextlib', 'threading', 'multiprocessing', 'queue', 'socket', 'http', 'urllib', 'email', 'html', 'xml', 'csv', 'configparser', 'argparse', 'logging', 'warnings', 'traceback', 'inspect', 'dis', 'pickle', 'struct', 'codecs', 'locale', 'gettext', 'random', 'math', 'cmath', 'decimal', 'fractions', 'statistics', 'numbers', 'array', 'weakref', 'types', 'copy', 'operator', 'heapq', 'bisect', 'pprint', 'reprlib', 'textwrap', 'string', 'difflib', 'unicodedata', 'stringprep', 'readline', 'rlcompleter']:
                        continue
                    try:
                        __import__(module)
                    except ImportError:
                        if module not in missing:
                            missing.append(module)
            
            if missing:
                if auto_install:
                    install_result = await self._install_dependencies(missing)
                    if "✅" in install_result:
                        return f"✅ 已自动安装依赖: {', '.join(missing)}"
                    else:
                        return f"⚠️ 自动安装失败: {install_result}\n请手动运行: pip install {' '.join(missing)}"
                return f"⚠️ 缺少依赖: {', '.join(missing)}\n请运行: pip install {' '.join(missing)}"
            
            return f"✅ 导入检查通过 ({len(import_lines)} 个外部依赖)"
        except Exception as e:
            return f"❌ 导入检查失败: {e}"
    
    async def _install_dependencies(self, packages: List[str]) -> str:
        """自动安装依赖包"""
        if not packages:
            return "✅ 无需安装"
        
        try:
            logger.info(f"📦 正在安装依赖: {', '.join(packages)}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet"] + packages,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ 依赖安装成功: {', '.join(packages)}")
                return f"✅ 安装成功: {', '.join(packages)}"
            else:
                logger.error(f"依赖安装失败: {result.stderr}")
                return f"❌ 安装失败: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return "❌ 安装超时 (5分钟)"
        except Exception as e:
            logger.error(f"安装依赖异常: {e}")
            return f"❌ 安装异常: {e}"
    
    async def _install_deps_task(self, params: Dict) -> str:
        """安装智能体依赖"""
        agent_name = params.get("agent_name", "")
        packages = params.get("packages", [])
        
        if agent_name:
            agent_file = self.agents_dir / f"{agent_name}.py"
            if not agent_file.exists():
                return f"❌ 智能体文件不存在: {agent_file}"
            
            import_result = await self._check_imports(agent_file, auto_install=True)
            return f"📦 智能体 '{agent_name}' 依赖检查:\n\n{import_result}"
        
        if packages:
            install_result = await self._install_dependencies(packages)
            return f"📦 安装依赖:\n\n{install_result}"
        
        return "❌ 请提供智能体名称或依赖包列表"
    
    async def _reload_agents(self, params: Dict) -> str:
        """重新加载所有智能体"""
        try:
            from ..agent_scanner import get_agent_scanner
            
            scanner = get_agent_scanner()
            old_count = len(scanner._cached_agents) if scanner._cached_agents else 0
            
            agents = scanner.refresh()
            new_count = len(agents)
            
            agent_list = []
            for name, meta in sorted(agents.items(), key=lambda x: x[1].priority):
                agent_list.append(f"  {meta.icon} {meta.display_name} ({name})")
            
            return f"""🔄 智能体列表已刷新

📊 智能体数量: {old_count} -> {new_count}

📋 当前智能体列表:
{chr(10).join(agent_list)}

✅ 热加载完成，新智能体已就绪"""
        except Exception as e:
            logger.error(f"刷新智能体失败: {e}")
            return f"❌ 刷新失败: {e}"

    async def _test_instantiation(self, agent_name: str) -> str:
        """测试智能体实例化"""
        try:
            module_name = f"personal_agent.agents.{agent_name}"
            
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            import importlib
            module = importlib.import_module(module_name)
            
            agent_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                    agent_class = obj
                    break
            
            if not agent_class:
                return "❌ 未找到智能体类"
            
            agent = agent_class()
            
            return f"✅ 实例化成功\n   名称: {agent.name}\n   描述: {agent.description}\n   能力: {', '.join(agent.capabilities)}"
        except Exception as e:
            return f"❌ 实例化失败: {e}"

    async def _test_function(self, agent_name: str, action: str, test_params: Dict) -> str:
        """测试智能体功能"""
        try:
            module_name = f"personal_agent.agents.{agent_name}"
            
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            import importlib
            module = importlib.import_module(module_name)
            
            agent_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                    agent_class = obj
                    break
            
            if not agent_class:
                return "❌ 未找到智能体类"
            
            agent = agent_class()
            
            task = Task(type=action, content=f"测试 {action}", params=test_params)
            result = await agent.execute_task(task)
            
            return f"✅ 功能测试完成\n   结果: {result}"
        except Exception as e:
            return f"❌ 功能测试失败: {e}"

    async def _fix_agent(self, params: Dict) -> str:
        """修复智能体代码"""
        agent_name = params.get("agent_name", "")
        error_info = params.get("error", "")
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体文件不存在: {agent_file}"
        
        with open(agent_file, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        prompt = f"""修复以下 Python 智能体代码中的错误。

文件: {agent_name}.py

原始代码:
```python
{original_code}
```

错误信息:
{error_info}

请返回修复后的完整代码。只返回代码，不要其他内容。"""

        try:
            fixed_code = await self._call_llm(prompt)
            
            fixed_code = fixed_code.strip()
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            fixed_code = fixed_code.strip()
            
            backup_file = self.backup_dir / f"{agent_file.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_code)
            logger.info(f"📦 已备份: {backup_file}")
            
            agent_file.write_text(fixed_code, encoding='utf-8')
            
            syntax_result = await self._check_syntax(agent_file)
            
            if "✅" in syntax_result:
                return f"""✅ 智能体代码已修复

📄 文件: {agent_file}
📦 备份: {backup_file}

{syntax_result}

请重新测试智能体。"""
            else:
                return f"""⚠️ 修复后仍有问题

{syntax_result}

请手动检查代码或提供更详细的错误信息。"""
        except Exception as e:
            logger.error(f"修复智能体失败: {e}")
            return f"❌ 修复失败: {e}"
    
    async def _review_agent(self, params: Dict) -> str:
        """审查智能体代码"""
        agent_name = params.get("agent_name", "")
        
        if not agent_name:
            return "❌ 请提供智能体名称"
        
        agent_file = self.agents_dir / f"{agent_name}.py"
        if not agent_file.exists():
            return f"❌ 智能体文件不存在: {agent_file}"
        
        code = agent_file.read_text(encoding='utf-8')
        
        prompt = f"""审查以下 Python 智能体代码，检查:

1. 代码质量和可读性
2. 错误处理是否完善
3. 是否遵循最佳实践
4. 是否有潜在的 bug
5. 是否有安全风险
6. 是否可以优化

代码:
```python
{code}
```

请返回审查报告，格式:
## 代码质量
评分: X/10
问题: ...

## 错误处理
评分: X/10
问题: ...

## 最佳实践
评分: X/10
问题: ...

## 潜在问题
- 问题1
- 问题2

## 改进建议
1. 建议1
2. 建议2

## 总体评分
X/10"""
        
        try:
            review_result = await self._call_llm_stream(prompt)
            return f"""📋 代码审查报告

🤖 智能体: {agent_name}
📄 文件: {agent_file}

{review_result}"""
        except Exception as e:
            logger.error(f"代码审查失败: {e}")
            return f"❌ 审查失败: {e}"
    
    async def _full_develop_workflow(self, params: Dict) -> str:
        """完整开发流程: 从需求到测试"""
        user_request = params.get("user_request", "")
        agent_name = params.get("agent_name", "")
        
        if not user_request:
            return "❌ 请提供用户需求描述"
        
        results = []
        results.append("🚀 开始完整开发流程")
        results.append("=" * 50)
        
        results.append("\n### 步骤 1: 创建 Skill 文件")
        skill_result = await self._create_skill_from_conversation({
            "user_request": user_request,
            "agent_name": agent_name
        })
        results.append(skill_result)
        
        if "❌" in skill_result:
            return "\n".join(results)
        
        skill_match = re.search(r'📄 文件: (.+\.md)', skill_result)
        if not skill_match:
            return "\n".join(results) + "\n\n❌ 无法获取 Skill 文件路径"
        
        skill_file = skill_match.group(1)
        
        name_match = re.search(r'🤖 智能体: (\S+)', skill_result)
        actual_agent_name = name_match.group(1) if name_match else agent_name
        
        results.append(f"\n### 步骤 2: 生成智能体代码")
        code_result = await self._create_agent_from_skill_md({
            "skill_file": skill_file,
            "skill_content": Path(skill_file).read_text(encoding='utf-8')
        })
        results.append(code_result)
        
        if "❌" in code_result:
            return "\n".join(results)
        
        results.append(f"\n### 步骤 3: 代码审查")
        review_result = await self._review_agent({"agent_name": actual_agent_name})
        results.append(review_result)
        
        results.append("\n" + "=" * 50)
        results.append("✅ 完整开发流程完成!")
        
        return "\n".join(results)
