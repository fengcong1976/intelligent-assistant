"""
Tool-Based Intent Parser - 基于工具查询的意图解析器

核心理念：
- 不再一次性发送所有工具定义给LLM
- 提供 query_tools 工具让LLM按需查询
- LLM 先查询工具，再选择使用
- 大幅减少 token 消耗

优化点：
1. 动态生成工具示例：从工具注册表中动态生成示例，不再硬编码
2. 智能示例生成：根据工具的参数定义生成合适的示例值
3. 缓存机制：缓存生成的系统提示和工具示例，避免重复生成
4. 参数智能匹配：根据参数名称和描述智能生成示例值
5. 用户输入示例：为每个工具生成多个用户输入示例，帮助LLM理解用法

工作流程：
1. 完全匹配快速跳转：检查用户输入是否完全匹配某个智能体的关键词
2. 关键词预筛选：根据用户输入中的关键词预筛选相关工具
3. 如果预筛选成功：直接将筛选后的工具发送给LLM选择
4. 如果预筛选失败：让LLM自行判断是否需要工具
5. LLM选择工具后：返回工具调用结果
"""
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
import json
import re
import importlib

from ..llm.base import BaseLLMProvider, ToolDefinition
from ..tools.agent_tools import get_tools_registry, AgentTool


@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_name: str
    arguments: Dict[str, Any]
    agent_name: str
    need_history: bool = False
    history_query: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None  # 如果不需要工具，LLM 可以直接返回答案
    is_quick_jump: bool = False  # 是否为快速跳转匹配的结果


@dataclass
class WorkflowResult:
    """工作流结果 - 多工具调用"""
    steps: List[ToolCallResult]
    is_workflow: bool = True
    original_text: str = ""


class ToolBasedIntentParser:
    """
    基于工具查询的意图解析器
    
    工作流程：
    1. 提供 query_tools 工具给 LLM
    2. LLM 按需查询相关工具
    3. LLM 选择合适的工具执行
    
    优化：支持关键词预筛选，跳过第一次LLM调用
    """
    
    def __init__(self, llm: BaseLLMProvider = None):
        self.llm = llm
        self.registry = get_tools_registry()
        self._system_prompt_cache = None
        self._tool_examples_cache = None
        self._system_prompt_cache_dict = {}  # 为不同工具组合缓存系统提示
        self._result_cache = {}  # 缓存解析结果，避免重复调用 LLM
        self._cache_key = None  # 当前请求的缓存键
    
    def clear_cache(self):
        """清除缓存，当工具注册表更新时调用"""
        self._system_prompt_cache = None
        self._tool_examples_cache = None
        logger.debug("工具示例缓存已清除")
    
    def validate_tool_examples(self) -> Dict[str, Any]:
        """验证所有工具示例是否正确
        
        Returns:
            Dict: 包含验证结果的字典
                - total: 总工具数
                - valid: 有效工具数
                - invalid: 无效工具数
                - errors: 错误列表
        """
        result = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": []
        }
        
        for tool in self.registry.get_all_tools():
            result["total"] += 1
            
            try:
                example = self._generate_tool_example(tool)
                if example:
                    result["valid"] += 1
                    logger.debug(f"✅ 工具示例验证成功: {tool.name}")
                else:
                    result["invalid"] += 1
                    result["errors"].append(f"{tool.name}: 生成示例失败")
                    logger.warning(f"⚠️ 工具示例验证失败: {tool.name}")
            except Exception as e:
                result["invalid"] += 1
                result["errors"].append(f"{tool.name}: {str(e)}")
                logger.error(f"❌ 工具示例验证异常: {tool.name} - {e}")
        
        logger.info(f"📊 工具示例验证完成: 总计={result['total']}, 有效={result['valid']}, 无效={result['invalid']}")
        return result
    
    def _get_system_prompt(self, matched_tools: Optional[List[AgentTool]] = None) -> str:
        """动态生成系统提示，从工具注册表中获取示例（带缓存）
        
        Args:
            matched_tools: 匹配的工具列表，如果提供则只为这些工具生成示例
        """
        # 如果有匹配的工具，生成一个缓存键
        cache_key = None
        if matched_tools:
            cache_key = "_".join(sorted([t.name for t in matched_tools]))
            if cache_key in self._system_prompt_cache_dict:
                return self._system_prompt_cache_dict[cache_key]
        
        # 如果没有匹配的工具，使用默认缓存
        if not matched_tools and self._system_prompt_cache is not None:
            return self._system_prompt_cache
        
        base_prompt = """根据用户输入，判断是否需要调用工具。

【核心规则】
1. 能直接回答的问题（知识、翻译、闲聊等）直接回答，不调用工具
2. 需要实时数据、特定操作、外部系统、文件操作时调用工具
3. 工具名称固定，用参数控制行为（如play_music(action="next")）
4. 【非常重要】如果系统提供了工具列表，必须从提供的工具中选择，不能选择其他工具
5. 【非常重要】必须返回工具调用格式：tool_name(param1="value1", param2="value2")，不能返回自然语言
6. 【非常重要】不能返回占位符或示例格式（如 tool_name(param1="value1")），必须返回实际的工具调用和参数值

【联系人信息提取规则 - 非常重要】
当用户提到添加联系人时，必须提取以下信息：
- 姓名：联系人的名字（如"小乱了"、"张三"）
- 邮箱：邮箱地址（如"1000@qq.com"）
- 电话：电话号码（如"13800138000"）
- 关系：关系描述（如"朋友"、"同事"、"领导"、"家人"、"同学"）

示例：
- "添加 小乱了 1000@qq.com 朋友 到通讯录" -> contact_add(name="小乱了", email="1000@qq.com", relationship="朋友")
- "保存老板 234566@qq.com 领导" -> contact_add(name="老板", email="234566@qq.com", relationship="领导")
- "添加张三 13800138000 同事" -> contact_add(name="张三", phone="13800138000", relationship="同事")

【多工具调用规则 - 非常重要】
当用户请求包含多个操作时，必须同时调用所有相关工具，用逗号分隔：

- "保存/生成/存成" + "发送/发到/发给" = save_document + send_email
- "生成图片/照片" + "发送/发到/发给" = generate_image + send_email
- "写...并...发到..." = save_document + send_email
- "生成...并发给..." = generate_image + send_email

【参数传递规则】
使用 {工具名.参数名} 格式传递前一个工具的输出：
- {save_document.file_path} = save_document返回的file_path
- {generate_image.first_file_path} = generate_image返回的first_file_path

【返回格式要求】
- 必须使用工具调用格式：tool_name(param1="value1", param2="value2")
- 示例：query_stock(stock_code="平安银行")、contact_add(name="张三", email="xxx@qq.com", relationship="朋友")
- 不能返回自然语言描述
- 不能选择未提供的工具
- 不能返回示例格式（如 tool_name(param1="value1")），必须返回实际工具调用

【单工具示例】"""
        
        # 从工具注册表生成示例（只为匹配的工具生成）
        if matched_tools:
            examples = self._generate_tool_examples_for_tools(matched_tools)
        else:
            examples = self._generate_tool_examples()
        
        result = base_prompt + examples
        
        # 缓存结果
        if matched_tools and cache_key:
            self._system_prompt_cache_dict[cache_key] = result
        elif not matched_tools:
            self._system_prompt_cache = result
        
        return result
    
    def _generate_tool_examples(self) -> str:
        """从工具注册表生成示例（带缓存）"""
        if self._tool_examples_cache is not None:
            return self._tool_examples_cache
        
        examples = []
        
        # 为每个工具生成示例
        for tool in self.registry.get_all_tools():
            example = self._generate_tool_example(tool)
            if example:
                examples.append(example)
        
        self._tool_examples_cache = "\n".join(examples)
        return self._tool_examples_cache
    
    def _generate_tool_examples_for_tools(self, tools: List[AgentTool]) -> str:
        """只为指定的工具生成示例（不缓存）"""
        examples = []
        
        # 只为指定的工具生成示例
        for tool in tools:
            example = self._generate_tool_example(tool)
            if example:
                examples.append(example)
        
        # 如果同时有save_document和send_email，添加组合示例
        tool_names = [tool.name for tool in tools]
        if "save_document" in tool_names and "send_email" in tool_names:
            examples.append("\n多工具组合示例：")
            examples.append("用户: 写一篇关于西安钟楼的介绍并保存成pdf格式发到小聪聪邮箱 -> save_document(content=\"西安钟楼介绍\", filename=\"西安钟楼.pdf\"), send_email(to=\"小聪聪\", attachment=\"{save_document.file_path}\")")
            examples.append("用户: 写一份报告保存成word格式发给张三 -> save_document(content=\"报告内容\", filename=\"报告.docx\"), send_email(to=\"张三\", attachment=\"{save_document.file_path}\")")
            examples.append("用户: 生成一份文档并保存成pdf发给我 -> save_document(content=\"文档内容\", filename=\"文档.pdf\"), send_email(to=\"我\", attachment=\"{save_document.file_path}\")")
        elif "generate_image" in tool_names and "send_email" in tool_names:
            examples.append("\n多工具组合示例：")
            examples.append("用户: 生成一张荷花照片并发给傅总 -> generate_image(prompt=\"荷花照片\"), send_email(to=\"傅总\", attachment=\"{generate_image.first_file_path}\")")
            examples.append("用户: 生成一张西安钟楼的图片并发到小聪聪邮箱 -> generate_image(prompt=\"西安钟楼\"), send_email(to=\"小聪聪\", attachment=\"{generate_image.first_file_path}\")")
            examples.append("用户: 生成一张风景照片发给我 -> generate_image(prompt=\"风景照片\"), send_email(to=\"我\", attachment=\"{generate_image.first_file_path}\")")
        
        return "\n".join(examples)
    
    def _generate_tool_example(self, tool) -> Optional[str]:
        """为单个工具生成示例（动态生成，不硬编码）"""
        try:
            tool_name = tool.name
            description = tool.description
            parameters = tool.parameters
            
            logger.debug(f"🔧 生成工具示例: {tool_name}")
            
            # 从工具描述和参数中提取关键信息
            examples = []
            
            # 获取参数信息
            props = parameters.get("properties", {})
            required = parameters.get("required", [])
            
            # 为每个必需参数生成示例
            if props:
                for param_name, param_info in props.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    
                    # 根据参数类型和描述生成示例值
                    example_value = self._generate_example_value(param_name, param_type, param_desc, tool_name)
                    
                    if example_value:
                        examples.append(f"{tool_name}({param_name}=\"{example_value}\")")
            
            # 如果没有参数或示例生成失败，生成一个简单的示例
            if not examples:
                examples.append(f"{tool_name}()")
            
            # 生成用户输入示例
            user_inputs = self._generate_user_input_examples(tool_name, description, props)
            
            # 组合示例
            result_lines = []
            for i, (user_input, tool_call) in enumerate(zip(user_inputs, examples)):
                result_lines.append(f"用户: {user_input} -> {tool_call}")
            
            result = "\n".join(result_lines[:2])  # 最多返回2个示例
            logger.debug(f"✅ 工具示例生成成功: {tool_name}")
            return result
            
        except Exception as e:
            logger.warning(f"❌ 生成工具示例失败 {tool.name}: {e}")
            return None
    
    def _generate_example_value(self, param_name: str, param_type: str, param_desc: str, tool_name: str) -> str:
        """根据参数类型和描述生成示例值"""
        param_desc_lower = param_desc.lower()
        
        # 根据参数名称和描述生成示例值
        if param_name == "city":
            return "北京"
        elif param_name == "days":
            return "0"
        elif param_name == "song" or "歌曲" in param_desc:
            return "稻香"
        elif param_name == "artist" or "歌手" in param_desc:
            return "周杰伦"
        elif param_name == "recipient_name" or "收件人" in param_desc:
            return "张三"
        elif param_name == "message" or "消息" in param_desc:
            return "你好"
        elif param_name == "prompt" or "描述" in param_desc:
            return "荷花照片"
        elif param_name == "size" or "分辨率" in param_desc:
            return "1920*1080"
        elif param_name == "stock_code" or "股票" in param_desc:
            return "伊利股份"
        elif param_name == "index_name" or "指数" in param_desc:
            return "大盘"
        elif param_name == "query" or "搜索" in param_desc:
            return "周杰伦"
        elif param_name == "video_name" or "视频" in param_desc:
            return "电影名"
        elif param_name == "category" or "类别" in param_desc:
            return "综合"
        elif param_name == "app_name" or "应用" in param_desc:
            return "QQ"
        elif param_name == "action":
            return "play"
        elif param_name == "text" or "文本" in param_desc:
            return "要播报的文本"
        elif param_name == "command" or "命令" in param_desc:
            return "命令"
        elif param_name == "entity_id":
            return "light.living_room"
        elif param_name == "temperature" or "温度" in param_desc:
            return "25"
        elif param_name == "brightness" or "亮度" in param_desc:
            return "100"
        elif param_name == "drive" or "盘符" in param_desc:
            return "E"
        elif param_name == "file_type" or "文件类型" in param_desc:
            return "mp3"
        elif param_name == "name" or "姓名" in param_desc:
            return "张三"
        elif param_name == "email" or "邮箱" in param_desc:
            return "xxx@xx.com"
        elif param_name == "phone" or "电话" in param_desc:
            return "13800138000"
        elif param_name == "relationship" or "关系" in param_desc:
            return "朋友"
        elif param_name == "destination" or "目的地" in param_desc:
            return "西安"
        elif param_name == "url" or "链接" in param_desc:
            return "下载链接"
        elif param_name == "filename" or "文件名" in param_desc:
            return "文档.pdf"
        elif param_name == "content" or "内容" in param_desc:
            return "文档内容"
        else:
            return "示例值"
    
    def _generate_user_input_examples(self, tool_name: str, description: str, props: dict) -> List[str]:
        """生成用户输入示例"""
        user_inputs = []
        
        # 根据工具名称和描述生成用户输入示例
        if tool_name == "get_weather":
            user_inputs.extend(["今天天气", "明天天气"])
        elif tool_name == "play_music":
            user_inputs.extend(["播放音乐", "下一首", "播放周杰伦的歌", "播放稻香"])
        elif tool_name == "send_email":
            user_inputs.extend(["发送邮件", "发到小聪聪邮箱", "发给张三", "发邮件给我", "发送到邮箱"])
        elif tool_name == "generate_image":
            user_inputs.extend(["生成一张荷花照片", "生成一张1920*1080的荷花照片"])
        elif tool_name == "query_stock":
            user_inputs.extend(["伊利股份股票行情", "中国人寿股票", "美的集团股票行情", "平安银行股票", "000001股票", "贵州茅台股价"])
        elif tool_name == "query_index":
            user_inputs.extend(["今天大盘怎么样", "大盘指数", "上证指数"])
        elif tool_name == "web_search":
            user_inputs.append("搜索周杰伦")
        elif tool_name == "play_video":
            user_inputs.extend(["播放视频", "播放电影"])
        elif tool_name == "get_news":
            user_inputs.append("查看新闻")
        elif tool_name == "open_app":
            user_inputs.extend(["打开QQ", "打开微信"])
        elif tool_name == "system_control":
            user_inputs.extend(["关机", "重启"])
        elif tool_name == "clipboard_write":
            user_inputs.append("复制文本")
        elif tool_name == "take_screenshot":
            user_inputs.append("截图")
        elif tool_name == "check_calendar":
            user_inputs.append("查看日历")
        elif tool_name == "download_file":
            user_inputs.append("下载文件")
        elif tool_name == "create_travel_plan":
            user_inputs.extend(["西安三天旅游攻略", "北京五天旅游攻略"])
        elif tool_name == "tts_speak":
            user_inputs.append("语音播报")
        elif tool_name == "developer_task":
            user_inputs.extend(["生成代码", "执行命令"])
        elif tool_name == "ha_control":
            user_inputs.append("打开客厅灯")
        elif tool_name == "ha_set_temperature":
            user_inputs.append("设置温度")
        elif tool_name == "ha_set_brightness":
            user_inputs.append("设置亮度")
        elif tool_name == "ha_query_state":
            user_inputs.append("查询状态")
        elif tool_name == "shopping_query":
            user_inputs.append("搜索商品")
        elif tool_name == "search_files":
            user_inputs.append("搜索文件")
        elif tool_name == "get_disk_space":
            user_inputs.append("E盘空间")
        elif tool_name == "add_contact":
            user_inputs.extend(["添加联系人", "添加 小乱了 1000@qq.com 朋友 到通讯录", "保存老板 234566@qq.com 领导", "添加张三 13800138000 同事"])
        elif tool_name == "query_contact":
            user_inputs.append("查询联系人")
        elif tool_name == "list_contacts":
            user_inputs.append("列出联系人")
        elif tool_name == "save_document":
            user_inputs.extend(["保存文档", "生成pdf文档", "保存成pdf", "生成word文档", "保存为excel"])
        else:
            user_inputs.append(description[:20])
        
        return user_inputs[:3]  # 最多返回3个示例
    
    async def parse(self, user_input: str, context: Dict[str, Any] = None) -> Optional[ToolCallResult]:
        result = await self.parse_all(user_input, context)
        if isinstance(result, WorkflowResult) and result.steps:
            return result.steps[0]
        return result
    
    async def parse_all(self, user_input: str, context: Dict[str, Any] = None, master=None):
        """解析用户输入，通过工具查询机制选择工具"""
        import time
        start_time = time.time()
        
        if not self.llm:
            from ..llm import LLMGateway
            from ..config import LLMConfig
            config = LLMConfig()
            self.llm = LLMGateway(config)
        
        # 生成缓存键（包含用户输入和上下文）
        cache_key = f"{user_input}_{str(context)}"
        self._cache_key = cache_key
        
        # 检查缓存
        if cache_key in self._result_cache:
            logger.info(f"💾 使用缓存结果: {cache_key[:50]}...")
            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
            return self._result_cache[cache_key]
        
        # 检查是否为确认关键词
        if master and hasattr(master, '_pending_action') and master._pending_action:
            confirm_keywords = ["好的", "可以", "行", "是的", "确认", "确定", "好", "OK", "ok", "Ok"]
            if user_input.strip() in confirm_keywords:
                logger.info(f"✅ 用户确认执行待处理操作")
                # 返回一个特殊的工具调用结果，表示需要执行待处理操作
                return ToolCallResult(
                    tool_name="confirm_action",
                    arguments={"original_text": user_input},
                    agent_name="master",
                    need_history=False,
                    history_query=None,
                    answer="CONFIRM"
                )
        
        # 检查是否为帮助请求（@智能体 /？ 或 @智能体 /?）
        if master and user_input.strip().startswith("@"):
            help_patterns = ['/?', '/？', '?', '？', 'help', '帮助']
            request_clean = user_input.strip().lower()
            # 检查是否是 @智能体 /？ 格式
            if any(request_clean.endswith(p) for p in help_patterns):
                logger.info(f"💡 检测到帮助请求: {user_input}")
                # 返回一个特殊的工具调用结果，表示需要显示帮助信息
                return ToolCallResult(
                    tool_name="agent_help",
                    arguments={"original_text": user_input},
                    agent_name="master",
                    need_history=False,
                    history_query=None,
                    answer="HELP"
                )
        
        # 完全匹配快速跳转：检查用户输入是否完全匹配某个智能体的关键词
        exact_match_result = self._check_exact_match(user_input)
        if exact_match_result:
            logger.info(f"⚡ 完全匹配快速跳转: {user_input} -> {exact_match_result['tool_name']}")
            result = ToolCallResult(
                tool_name=exact_match_result['tool_name'],
                arguments=exact_match_result['arguments'],
                agent_name=exact_match_result['agent_name'],
                need_history=False,
                history_query=None,
                is_quick_jump=True
            )
            # 缓存结果
            if self._cache_key:
                self._result_cache[self._cache_key] = result
            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
            return result
        
        context_info = ""
        if context:
            files = context.get("files", [])
            if files:
                context_info = f"\n\n【附件信息】用户已提供以下附件文件：\n" + "\n".join(f"- {f}" for f in files)
        
        # 分析用户输入中的操作关键词
        operation_analysis = self._analyze_operations(user_input)
        if operation_analysis:
            context_info += f"\n\n【操作分析】检测到以下操作：{operation_analysis}"
            logger.info(f"🔍 操作分析结果: {operation_analysis}")
        
        # 如果检测到多个操作，添加明确指示
        if operation_analysis and "、" in operation_analysis:
            context_info += f"\n\n【重要提示】检测到多个操作，请调用所有相关工具，不要只选择其中一个！"
        
        try:
            matched_tools = self._pre_filter_tools(user_input)
            
            if matched_tools:
                logger.info(f"⚡ 关键词预筛选: 检测到关键词，跳过第一次LLM调用")
                logger.info(f"📚 预筛选工具: {[t.name for t in matched_tools]}")
                
                tool_defs = []
                for tool in matched_tools:
                    tool_defs.append(ToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.parameters
                    ))
                
                logger.info(f"🔧 传递给 LLM 的工具定义: {[t.name for t in tool_defs]}")
                for tool_def in tool_defs:
                    logger.info(f"   - {tool_def.name}: {tool_def.description[:100]}...")
                
                messages = [
                    {"role": "system", "content": self._get_system_prompt(matched_tools)},
                    {"role": "user", "content": user_input + context_info}
                ]
                
                logger.info(f"⏱️ [计时] 开始LLM调用 (直接选择工具)")
                t1 = time.time()
                response = await self.llm.chat(
                    messages,
                    tools=tool_defs,
                    tool_choice="auto"
                )
                logger.info(f"⏱️ [计时] LLM调用完成，耗时: {time.time() - t1:.2f}秒")
                
                # 如果检测到多个操作但LLM只返回了一个工具，强制调用所有相关工具
                if operation_analysis and "、" in operation_analysis and response.tool_calls and len(response.tool_calls) == 1:
                    logger.warning(f"⚠️ 检测到多个操作但LLM只返回了一个工具，强制调用所有相关工具")
                    logger.warning(f"⚠️ 操作分析: {operation_analysis}")
                    logger.warning(f"⚠️ 预筛选工具: {[t.name for t in matched_tools]}")
                    
                    # 创建多个工具调用
                    steps = []
                    for tool in matched_tools:
                        result = await self._handle_direct_tool_call(
                            type('ToolCall', (), {
                                'name': tool.name,
                                'arguments': {}
                            }),
                            user_input
                        )
                        if result:
                            steps.append(result)
                    
                    if steps:
                        logger.info(f"✅ 强制调用 {len(steps)} 个工具: {[s.tool_name for s in steps]}")
                        logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                        
                        if len(steps) == 1:
                            return steps[0]
                        
                        return WorkflowResult(
                            steps=steps,
                            is_workflow=True,
                            original_text=user_input
                        )
                
                if response.usage:
                    prompt_tokens = response.usage.get("prompt_tokens", 0)
                    completion_tokens = response.usage.get("completion_tokens", 0)
                    total_tokens = response.usage.get("total_tokens", 0)
                    logger.info(f"📊 Token 统计: 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
                    try:
                        from ..utils.token_counter import update_token_count
                        update_token_count(total_tokens)
                    except Exception as e:
                        logger.error(f"Token更新失败: {e}")
                
                if response.tool_calls:
                    tool_calls_count = len(response.tool_calls)
                    logger.info(f"📊 LLM 返回 {tool_calls_count} 个工具调用: {[tc.name for tc in response.tool_calls]}")
                    
                    # 验证 LLM 返回的工具是否在预筛选列表中
                    valid_tool_names = [t.name for t in matched_tools]
                    invalid_tools = [tc.name for tc in response.tool_calls if tc.name not in valid_tool_names]
                    
                    if invalid_tools:
                        logger.warning(f"⚠️ LLM 返回了不在预筛选列表中的工具: {invalid_tools}")
                        logger.warning(f"⚠️ 预筛选工具: {valid_tool_names}")
                        logger.warning(f"⚠️ 强制使用预筛选的第一个工具: {matched_tools[0].name}")
                        
                        # 强制使用预筛选的第一个工具
                        result = await self._handle_direct_tool_call(
                            type('ToolCall', (), {
                                'name': matched_tools[0].name,
                                'arguments': {}
                            }),
                            user_input
                        )
                        if result and self._cache_key:
                            self._result_cache[self._cache_key] = result
                        logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                        return result
                    
                    if tool_calls_count == 1:
                        result = await self._handle_direct_tool_call(response.tool_calls[0], user_input)
                        if result and self._cache_key:
                            self._result_cache[self._cache_key] = result
                        logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                        return result
                    else:
                        steps = []
                        for tool_call in response.tool_calls:
                            result = await self._handle_direct_tool_call(tool_call, user_input)
                            if result:
                                steps.append(result)
                        
                        if steps:
                            logger.info(f"✅ 多工具调用: {[s.tool_name for s in steps]}")
                            if self._cache_key:
                                self._result_cache[self._cache_key] = WorkflowResult(
                                    steps=steps,
                                    is_workflow=True,
                                    original_text=user_input
                                )
                            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                            return WorkflowResult(
                                steps=steps,
                                is_workflow=True,
                                original_text=user_input
                            )
                
                if response.content and not response.tool_calls:
                    logger.info(f"💬 LLM 返回文本内容，解析工具调用")
                    logger.info(f"💬 LLM 返回的文本: {response.content[:500]}...")
                    
                    all_tool_calls = self._parse_tool_calls_from_text(response.content)
                    
                    logger.info(f"💬 从文本中解析出 {len(all_tool_calls)} 个工具调用: {[tc[0] for tc in all_tool_calls]}")
                    
                    if len(all_tool_calls) == 0:
                        logger.info(f"💬 LLM 直接返回答案，不需要工具")
                        logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                        return ToolCallResult(
                            tool_name="general",
                            agent_name="master",
                            arguments={"message": user_input, "answer": response.content},
                            answer=response.content
                        )
                    
                    if len(all_tool_calls) == 1:
                        tool_name, params = all_tool_calls[0]
                        tool = self.registry.get_tool(tool_name)
                        if tool:
                            params["original_text"] = user_input
                            result = ToolCallResult(
                                tool_name=tool_name,
                                arguments=params,
                                agent_name=tool.agent_name,
                                need_history=False
                            )
                            if self._cache_key:
                                self._result_cache[self._cache_key] = result
                            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                            return result
                    else:
                        steps = []
                        for tool_name, params in all_tool_calls:
                            tool = self.registry.get_tool(tool_name)
                            if tool:
                                params["original_text"] = user_input
                                steps.append(ToolCallResult(
                                    tool_name=tool_name,
                                    arguments=params,
                                    agent_name=tool.agent_name,
                                    need_history=False
                                ))
                        
                        if steps:
                            logger.info(f"✅ 从文本解析出多工具调用: {[s.tool_name for s in steps]}")
                            if self._cache_key:
                                self._result_cache[self._cache_key] = WorkflowResult(
                                    steps=steps,
                                    is_workflow=True,
                                    original_text=user_input
                                )
                            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                            return WorkflowResult(
                                steps=steps,
                                is_workflow=True,
                                original_text=user_input
                            )
                
                logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                return None
            
            # 预筛选没有匹配到工具，不发送工具列表，让 LLM 自己判断
            logger.info(f"💭 预筛选未匹配工具，让 LLM 自行判断是否需要工具")
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_input + context_info}
            ]
            
            logger.info(f"⏱️ [计时] 开始LLM调用 (无工具)")
            t1 = time.time()
            response = await self.llm.chat(
                messages,
                tool_choice="auto"
            )
            logger.info(f"⏱️ [计时] LLM调用完成，耗时: {time.time() - t1:.2f}秒")
            
            if response.usage:
                prompt_tokens = response.usage.get("prompt_tokens", 0)
                completion_tokens = response.usage.get("completion_tokens", 0)
                total_tokens = response.usage.get("total_tokens", 0)
                logger.info(f"📊 Token 统计: 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
                try:
                    from ..utils.token_counter import update_token_count
                    update_token_count(total_tokens)
                except Exception as e:
                    logger.error(f"Token更新失败: {e}")
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    result = await self._handle_direct_tool_call(tool_call, user_input)
                    logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                    return result
            
            # 如果 LLM 返回了文本内容（没有 tool_calls），检查是否包含工具调用
            if response.content and not response.tool_calls:
                logger.info(f"💬 LLM 返回文本内容，检查是否包含工具调用")
                logger.info(f"💬 LLM 返回的文本: {response.content[:500]}...")
                
                # 检查文本中是否包含工具调用
                tool_call_pattern = r'(\w+)\((.*?)\)'
                match = re.match(tool_call_pattern, response.content.strip())
                
                if match:
                    tool_name = match.group(1)
                    params_str = match.group(2)
                    
                    logger.info(f"🔧 检测到文本中的工具调用: {tool_name}")
                    logger.info(f"🔧 参数字符串: {params_str}")
                    
                    # 解析参数
                    params = {}
                    if params_str:
                        param_pattern = r'(\w+)="([^"]*)"'
                        for param_match in re.finditer(param_pattern, params_str):
                            param_name = param_match.group(1)
                            param_value = param_match.group(2)
                            params[param_name] = param_value
                            logger.debug(f"   解析参数: {param_name}={param_value}")
                    
                    logger.info(f"🔧 解析后的参数: {params}")
                    
                    # 从工具注册表获取对应的智能体
                    tool = self.registry.get_tool(tool_name)
                    
                    if tool:
                        logger.info(f"🎯 工具调用: {tool_name} -> {tool.agent_name}")
                        logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                        return ToolCallResult(
                            tool_name=tool_name,
                            arguments=params,
                            agent_name=tool.agent_name,
                            need_history=False,
                            history_query=None
                        )
                    else:
                        logger.warning(f"⚠️ 未找到工具: {tool_name}")
                
                # 如果不是工具调用，返回 general
                logger.info(f"💬 LLM 直接返回答案，不需要工具")
                logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
                return ToolCallResult(
                    tool_name="general",
                    agent_name="master",
                    arguments={"message": user_input, "answer": response.content},
                    answer=response.content
                )
            
            logger.info(f"⏱️ [计时] parse_all 总耗时: {time.time() - start_time:.2f}秒")
            return None
            
        except Exception as e:
            logger.error(f"工具选择失败: {e}")
            return None
    
    async def _select_and_execute_tool(self, messages: List[Dict], user_input: str):
        """让LLM根据查询结果选择并执行工具"""
        import time
        start_time = time.time()
        
        # 添加系统提示，确保 LLM 知道可以调用多个工具
        if not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {"role": "system", "content": self._get_system_prompt()})
        
        last_message = messages[-1]
        tools_info = last_message.get("content", "")
        
        matched_tools = []
        for line in tools_info.split('\n'):
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                tool_name = line[2:-2].strip()
                tool = self.registry.get_tool(tool_name)
                if tool:
                    matched_tools.append(tool)
                    logger.debug(f"解析到工具: {tool_name}")
        
        if not matched_tools:
            logger.warning("未能从查询结果解析出工具，使用全部工具")
            matched_tools = self.registry.get_all_tools()
        
        tool_defs = []
        for tool in matched_tools:
            tool_defs.append(ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters
            ))
        
        logger.info(f"📚 发送 {len(tool_defs)} 个相关工具给 LLM: {[t.name for t in matched_tools]}")
        
        logger.info(f"⏱️ [计时] 开始第二次LLM调用 (选择工具)")
        t1 = time.time()
        response = await self.llm.chat(
            messages,
            tools=tool_defs,
            tool_choice="auto"
        )
        logger.info(f"⏱️ [计时] 第二次LLM调用完成，耗时: {time.time() - t1:.2f}秒")
        
        if response.usage:
            prompt_tokens = response.usage.get("prompt_tokens", 0)
            completion_tokens = response.usage.get("completion_tokens", 0)
            total_tokens = response.usage.get("total_tokens", 0)
            logger.info(f"📊 Token 统计(执行阶段): 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
            try:
                from ..utils.token_counter import update_token_count
                update_token_count(total_tokens)
            except Exception:
                pass
        
        if not response.tool_calls:
            logger.info(f"LLM 未选择工具")
            return None
        
        logger.info(f"📊 LLM 返回 {len(response.tool_calls)} 个工具调用: {[tc.name for tc in response.tool_calls]}")
        
        if len(response.tool_calls) == 1:
            result = await self._handle_direct_tool_call(response.tool_calls[0], user_input)
            logger.info(f"⏱️ [计时] _select_and_execute_tool 总耗时: {time.time() - start_time:.2f}秒")
            return result
        
        steps = []
        for i, tool_call in enumerate(response.tool_calls):
            result = await self._handle_direct_tool_call(tool_call, user_input)
            if result:
                steps.append(result)
        
        if not steps:
            return None
        
        if len(steps) == 1:
            logger.info(f"⏱️ [计时] _select_and_execute_tool 总耗时: {time.time() - start_time:.2f}秒")
            return steps[0]
        
        logger.info(f"⏱️ [计时] _select_and_execute_tool 总耗时: {time.time() - start_time:.2f}秒")
        return WorkflowResult(
            steps=steps,
            is_workflow=True,
            original_text=user_input
        )
    
    async def _handle_direct_tool_call(self, tool_call, user_input: str) -> Optional[ToolCallResult]:
        """处理直接工具调用"""
        tool_name = tool_call.name
        arguments = tool_call.arguments
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            logger.warning(f"未知工具: {tool_name}")
            return None
        
        arguments["original_text"] = user_input
        
        logger.info(f"🎯 LLM 选择工具: {tool_name} -> {tool.agent_name}")
        logger.debug(f"   参数: {arguments}")
        
        return ToolCallResult(
            tool_name=tool_name,
            arguments=arguments,
            agent_name=tool.agent_name,
            need_history=False,
            history_query=None
        )
    
    def _check_exact_match(self, user_input: str) -> Optional[Dict[str, Any]]:
        """检查用户输入是否完全匹配某个工具的别名（必须是唯一的）
        
        支持两种模式：
        1. 完全匹配：用户输入完全等于别名
        2. 前缀匹配：用户输入以别名开头，后面跟着参数
        
        Args:
            user_input: 用户输入
            
        Returns:
            如果完全匹配且唯一，返回包含 tool_name, params, agent_name 的字典；否则返回 None
        """
        try:
            user_input_lower = user_input.lower().strip()
            
            # 收集所有匹配的工具
            matched_tools = []
            matched_alias = None
            matched_params = {}
            extra_param = None
            
            # 遍历所有工具，检查是否有完全匹配的别名
            for tool in self.registry.get_all_tools():
                # 检查工具名称是否匹配
                if tool.name.lower() == user_input_lower:
                    matched_tools.append(tool)
                    continue
                
                # 检查工具别名是否匹配
                for alias in tool.aliases:
                    alias_lower = alias.lower()
                    # 完全匹配
                    if alias_lower == user_input_lower:
                        matched_tools.append(tool)
                        matched_alias = alias
                        if tool.alias_params and alias in tool.alias_params:
                            matched_params = tool.alias_params[alias]
                        break
                    # 前缀匹配：用户输入以别名开头，后面跟着空格和参数
                    elif user_input_lower.startswith(alias_lower + " ") or user_input_lower.startswith(alias_lower + "　"):
                        matched_tools.append(tool)
                        matched_alias = alias
                        if tool.alias_params and alias in tool.alias_params:
                            matched_params = tool.alias_params[alias].copy()
                        # 提取别名后面的内容作为参数
                        extra_param = user_input[len(alias):].strip()
                        break
            
            # 如果没有匹配的工具，返回 None
            if not matched_tools:
                return None
            
            # 如果匹配了多个工具，说明不是唯一的，返回 None
            if len(matched_tools) > 1:
                logger.debug(f"⚠️ 关键词 '{user_input}' 匹配了多个工具: {[t.name for t in matched_tools]}，不进行快速跳转")
                return None
            
            # 只有一个匹配的工具，返回结果
            tool = matched_tools[0]
            logger.info(f"✅ 完全匹配唯一工具: {user_input} -> {tool.agent_name}.{tool.name}")
            
            # 如果有额外参数，根据工具的参数定义智能匹配
            if extra_param:
                # 获取工具的参数定义
                tool_params = tool.parameters.get("properties", {}) if tool.parameters else {}
                
                if tool_params:
                    # 优先查找名为 app_name 或 name 的参数
                    param_name = None
                    for key in ["app_name", "name", "query", "keyword", "text", "file_path", "device", "path"]:
                        if key in tool_params:
                            param_name = key
                            break
                    
                    # 如果没有找到常用参数名，使用第一个参数
                    if not param_name and tool_params:
                        param_name = list(tool_params.keys())[0]
                    
                    if param_name:
                        matched_params[param_name] = extra_param
                
                matched_params["original_text"] = user_input
            
            return {
                "tool_name": tool.name,
                "arguments": matched_params,
                "agent_name": tool.agent_name
            }
        except Exception as e:
            logger.error(f"检查完全匹配失败: {e}")
            return None
    
    def _pre_filter_tools(self, user_input: str) -> Optional[List[AgentTool]]:
        """根据关键词预筛选工具（动态从工具aliases获取，并添加额外的关键词映射）"""
        user_input_lower = user_input.lower()
        
        # 额外的关键词映射（为工具添加更多同义词）
        keyword_mapping = {
            "get_weather": ["天气", "气温", "下雨", "晴天", "阴天", "多云", "预报", "气温", "温度", "气候"],
            "query_stock": ["股票", "行情", "涨跌", "股价", "股市", "证券", "代码", "股份"],
            "query_index": ["大盘", "指数", "上证", "深证", "创业板", "沪深", "成指", "综指"],
            "check_calendar": ["日历", "日程", "安排", "计划", "预约", "会议", "提醒"],
            "create_travel_plan": ["旅游", "攻略", "行程", "游玩", "景点", "路线", "旅行"],
            "tts_speak": ["语音", "播报", "读出", "朗读", "说出来", "念"],
            "play_music": ["音乐", "歌曲", "播放", "听歌", "音乐播放器", "歌"],
            "play_video": ["视频", "电影", "播放视频", "看电影", "视频播放器", "影片"],
            "send_email": ["邮件", "邮箱", "发送邮件", "写信", "邮件发送"],
            "generate_image": ["图片", "照片", "生成", "画", "绘画", "图像"],
            "save_document": ["保存", "生成文档", "生成pdf", "保存成pdf", "保存为pdf", "生成word", "生成doc", "保存成doc", "保存为doc", "生成excel", "保存成excel", "保存为excel", "存成", "存为", "文档", "pdf", "word", "doc", "excel", "xlsx"],
            "web_search": ["搜索", "百度", "谷歌", "查找", "查询", "搜"],
            "get_news": ["新闻", "资讯", "消息", "新闻资讯", "时事"],
            "open_app": ["打开", "启动", "运行", "应用", "程序", "软件"],
            "system_control": ["关机", "重启", "锁屏", "睡眠", "系统控制"],
            "clipboard_write": ["复制", "剪贴板", "粘贴"],
            "take_screenshot": ["截图", "屏幕截图", "截屏", "屏幕捕捉"],
            "download_file": ["下载", "下载文件", "文件下载"],
            "developer_task": ["代码", "编程", "开发", "执行命令", "运行命令"],
            "ha_control": ["智能家居", "控制", "打开灯", "关闭灯", "家电"],
            "ha_set_temperature": ["温度", "空调", "调节温度", "设置温度"],
            "ha_set_brightness": ["亮度", "灯光", "调节亮度", "设置亮度"],
            "ha_query_state": ["状态", "查询状态", "查看状态", "设备状态"],
            "shopping_query": ["商品", "购物", "搜索商品", "买东西", "购买"]
        }
        
        matched_tools = []
        all_tools = self.registry.get_all_tools()
        
        for tool in all_tools:
            tool_keywords = [tool.name.lower()]
            
            # 添加工具别名
            if hasattr(tool, 'aliases') and tool.aliases:
                for alias in tool.aliases:
                    tool_keywords.append(alias.lower())
            
            # 添加额外的关键词映射
            if tool.name in keyword_mapping:
                tool_keywords.extend(keyword_mapping[tool.name])
            
            # 检查用户输入中是否包含任何关键词
            for keyword in tool_keywords:
                if keyword in user_input_lower:
                    matched_tools.append(tool)
                    logger.debug(f"   匹配工具: {tool.name} (关键词: {keyword})")
                    break
        
        logger.debug(f"   预筛选结果: {[t.name for t in matched_tools]}")
        return matched_tools if matched_tools else None
    
    def _parse_tool_calls_from_text(self, text: str) -> List[Tuple[str, Dict[str, str]]]:
        """从文本中解析工具调用，支持多工具调用
        
        Args:
            text: LLM返回的文本内容
            
        Returns:
            List of (tool_name, params) tuples
        """
        results = []
        
        # 匹配工具调用格式: tool_name(param1="value1", param2="value2")
        # 支持多个工具调用用逗号分隔
        tool_call_pattern = r'(\w+)\(([^)]*)\)'
        
        for match in re.finditer(tool_call_pattern, text):
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # 解析参数
            params = {}
            if params_str.strip():
                # 匹配 key="value" 格式的参数
                param_pattern = r'(\w+)="([^"]*)"'
                for param_match in re.finditer(param_pattern, params_str):
                    param_name = param_match.group(1)
                    param_value = param_match.group(2)
                    params[param_name] = param_value
            
            results.append((tool_name, params))
            logger.debug(f"   解析工具调用: {tool_name}({params})")
        
        return results
    
    def _analyze_operations(self, user_input: str) -> str:
        """分析用户输入中的操作关键词"""
        user_input_lower = user_input.lower()
        
        operations = []
        
        # 检测各种操作关键词
        if any(keyword in user_input_lower for keyword in ["保存", "生成", "存成", "存为", "文档", "pdf", "word", "doc", "excel", "xlsx"]):
            operations.append("生成/保存文档")
        
        if any(keyword in user_input_lower for keyword in ["发送", "发到", "发给", "邮箱", "邮件"]):
            operations.append("发送邮件")
        
        if any(keyword in user_input_lower for keyword in ["图片", "照片", "画", "绘画", "图像"]):
            operations.append("生成图片")
        
        if any(keyword in user_input_lower for keyword in ["音乐", "歌曲", "播放", "听歌"]):
            operations.append("播放音乐")
        
        if any(keyword in user_input_lower for keyword in ["视频", "电影", "影片"]):
            operations.append("播放视频")
        
        return "、".join(operations) if operations else ""
    
    def get_available_tools(self) -> List[str]:
        """获取所有可用工具名称"""
        return [tool.name for tool in self.registry.get_all_tools()]


async def parse_intent_with_tools(user_input: str, context: Dict[str, Any] = None) -> Optional[ToolCallResult]:
    parser = ToolBasedIntentParser()
    return await parser.parse(user_input, context)


async def parse_intent_with_tools_all(user_input: str, context: Dict[str, Any] = None, master=None):
    parser = ToolBasedIntentParser()
    return await parser.parse_all(user_input, context, master)
