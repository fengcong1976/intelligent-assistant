"""
Intent Parser - 用户意图解析器
使用 LLM 统一解析用户意图，支持工具调用查询历史
后处理阶段进行关键词替换
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from loguru import logger

from ..skills import skill_manager


class IntentType:
    """意图类型"""
    INSTALL_SOFTWARE = "install_software"
    DOWNLOAD_FILE = "download_file"
    SEARCH_WEB = "search_web"
    SKILL_MATCH = "skill_match"
    SEND_EMAIL = "send_email"
    PLAY_MUSIC = "play_music"
    PLAY_VIDEO = "play_video"
    CRAWLER_TASK = "crawler_task"
    WEATHER_QUERY = "weather_query"
    CONTACT_MANAGE = "contact_manage"
    FILE_OPERATION = "file_operation"
    DISK_SPACE = "disk_space"
    DEVELOPER_TASK = "developer_task"
    PDF_OPERATION = "pdf_operation"
    OS_CONTROL = "os_control"
    APP_CONTROL = "app_control"
    DOWNLOAD = "download"
    NEWS = "news"
    WEB_SERVER = "web_server"
    CALENDAR = "calendar"
    CREATE_SKILL = "create_skill"
    TTS = "tts"
    IMAGE_GENERATION = "image_generation"
    GENERAL = "general"


class IntentParser:
    """用户意图解析器 - 纯 LLM 驱动，后处理关键词替换"""

    def __init__(self):
        self._llm_gateway = None
        self._settings = None
        self._keyword_mappings_cache: Dict[str, tuple] = {}
    
    def _get_llm_gateway(self):
        if self._llm_gateway is None:
            from ..config import settings
            from ..llm import LLMGateway
            self._llm_gateway = LLMGateway(settings.llm)
            self._settings = settings
        return self._llm_gateway
    
    def _get_agent_capabilities(self) -> str:
        """动态获取所有智能体的能力描述"""
        try:
            from ..tools.agent_tools import get_tools_registry
            
            registry = get_tools_registry()
            tools = registry.get_all_tools()
            
            if not tools:
                return self._get_default_capabilities()
            
            # 按智能体分组工具
            agent_tools = {}
            for tool in tools:
                agent_name = tool.agent_name
                if agent_name not in agent_tools:
                    agent_tools[agent_name] = []
                agent_tools[agent_name].append(tool)
            
            lines = ["## 可用工具：\n"]
            
            for agent_name, agent_tool_list in agent_tools.items():
                lines.append(f"### {agent_name}")
                for tool in agent_tool_list:
                    lines.append(f"- {tool.name}: {tool.description}")
                lines.append("")
            
            lines.append("### general (通用对话)")
            lines.append("- 其他所有无法归类的对话")
            lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"动态获取智能体能力失败: {e}")
            return self._get_default_capabilities()
    
    def _get_action_hints(self) -> str:
        """获取操作提示，帮助 LLM 正确提取参数"""
        return """### 操作参数说明：

**music_agent 搜索音乐**:
- action=search, query=搜索关键词（歌曲名、歌手名等）
- 示例: "查找犯错这首歌" -> action=search, query="犯错"

**music_agent 播放音乐**:
- action=play, song_name=歌曲名（可选）, artist=歌手名（可选）
- 示例: "播放稻香" -> action=play, song_name="稻香"
- 示例: "播放周杰伦的歌" -> action=play, artist="周杰伦"
- 示例: "播放田震的野花" -> action=play, song_name="野花", artist="田震"

**email_agent 发送邮件**:
- action=send, recipient_name=收件人名称或邮箱, subject=主题（可选）, message=要转告的消息内容
- 示例: "给张三发邮件说明天开会" -> action=send, recipient_name="张三", message="明天开会"
- 示例: "给小聪聪发一份邮件，让他明天早上过来开会" -> action=send, recipient_name="小聪聪", message="明天早上过来开会"
- 注意：如果用户有明确要转告的内容，提取为message参数，不要让LLM生成内容

**weather_agent 查询天气**:
- action=current_weather/forecast, city=城市名, days=天数(0=今天,1=明天,2=后天)
- 示例: "北京明天天气" -> action=forecast, city="北京", days=1
- 示例: "明天北京天气" -> action=forecast, city="北京", days=1
- 示例: "北京明天的天气" -> action=forecast, city="北京", days=1
- 示例: "北京后天天气" -> action=forecast, city="北京", days=2
- 示例: "北京今天天气" -> action=current_weather, city="北京", days=0
- 示例: "北京天气" -> action=current_weather, city="北京", days=0
- 示例: "今天天气" -> action=current_weather, city="", days=0

**contact_agent 联系人操作**:
- action=add/query/list, name=姓名, email=邮箱, phone=电话, tags=标签
- 示例: "添加联系人张三邮箱xxx@xx.com" -> action=add, name="张三", email="xxx@xx.com"
- 示例: "老板 234566@qq.com 领导" -> action=add, name="老板", email="234566@qq.com", tags=["领导"]
- 示例: "保存联系人 王五 13800138000" -> action=add, name="王五", phone="13800138000"
- 示例: "查询张三的联系方式" -> action=query, name="张三"

**file_agent 文件操作**:
- action=disk_space/search_files, drive=盘符, file_type=文件类型
- 示例: "E盘空间" -> action=disk_space, drive="E"

**app_agent 应用操作**:
- action=open/close, app_name=应用名称
- 示例: "打开QQ" -> action=open, app_name="QQ"
- 示例: "打开微信" -> action=open, app_name="微信"
- 示例: "关闭QQ" -> action=close, app_name="QQ"
- 示例: "打开记事本" -> action=open, app_name="notepad"

**crawler_agent 网络操作**:
- action=search/crawl, query=搜索词, url=网址
- 示例: "搜索周杰伦" -> action=search, query="周杰伦"

**tts_agent 语音合成**:
- action=synthesize/synthesize_and_play/synthesize_and_send, text=要合成的文本, voice=音色（可选）
- 可用音色: longyue_v3(女声), longfei_v3(男声), longshuo_v3(沉稳男声), longyingjing_v3(京味女声), longjielidou_v3(童声)
- 示例: "把这句话合成MP3" -> action=synthesize, text="这句话"
- 示例: "把这句话合成MP3并播放" -> action=synthesize_and_play, text="这句话"
- 示例: "把这句话合成语音发到我邮箱" -> action=synthesize_and_send, text="这句话", recipient_name="我"
"""
    
    def _get_default_capabilities(self) -> str:
        """获取默认的智能体能力描述"""
        return """
## 可用智能体及其能力：

### 1. music_agent (音乐智能体)
- 播放音乐: action=play, song_name=歌曲名（可选）, artist=歌手名（可选）
- 暂停音乐: action=pause
- 停止音乐: action=stop
- 下一首: action=next
- 上一首: action=previous
- 继续播放: action=resume
- 搜索音乐: action=search, query=搜索词
- 支持格式: MP3, WAV, FLAC, M4A, OGG, WMA, NCM

### 2. video_agent (视频智能体)
- 播放视频: action=play, video_name=视频名（可选）
- 停止视频: action=stop
- 支持格式: MP4, AVI, MKV, MOV, WMV, FLV

### 3. email_agent (邮件智能体)
- 发送邮件: action=send, recipient_name=收件人名称或邮箱, message=要转告的消息
- 批量发送: action=send_to_relationship, relationship=关系类型
- 发送当前音乐: action=send_current_music, recipient_name=收件人

### 4. weather_agent (天气智能体)
- 查询天气: city=城市名, query_type=current/forecast

### 5. contact_agent (联系人智能体)
- 添加联系人: action=add, name=姓名, email=邮箱, phone=电话
- 查询联系人: action=query, name=姓名
- 列出联系人: action=list

### 6. file_agent (文件智能体)
- 磁盘空间查询: action=disk_space, drive=盘符
- 搜索文件: action=search_files, drive=盘符, file_type=文件类型

### 7. os_agent (系统智能体)
- 静音: action=volume_mute
- 取消静音: action=volume_unmute
- 音量增加: action=volume_up
- 音量降低: action=volume_down
- 查询音量: action=volume_get
- 关机: action=shutdown
- 重启: action=restart
- 锁屏: action=lock
- 休眠: action=sleep
- 截图: action=screenshot

### 8. crawler_agent (爬虫智能体)
- 网络搜索: action=search, query=搜索词
- 爬取网页: action=crawl, url=网址
- 提取视频链接: action=scrape_video_links, url=网址

### 9. developer_agent (开发智能体)
- 生成代码: action=generate_code, description=代码描述
- 执行CLI命令: action=cli_execute, command=命令

### 10. document_agent (文档智能体)
- 读取PDF: action=pdf_read, path=文件路径
- 生成PDF: action=pdf_generate, content=内容, title=标题
- 生成Word: action=doc_generate, content=内容, title=标题
- 生成Excel: action=excel_generate, content=内容, title=标题
- 保存文档: action=save_document, filename=文件名, content=内容（支持.docx/.xlsx/.pdf格式）
- PDF转Word: action=pdf_to_word, path=PDF文件路径（仅用于转换现有PDF）
- PDF转图片: action=pdf_to_image, path=PDF文件路径（仅用于转换现有PDF）
- Word转PDF: action=word_to_pdf, path=Word文件路径（仅用于转换现有Word）
- TXT转PDF: action=txt_to_pdf, path=TXT文件路径（仅用于转换现有TXT）
- 图片转PDF: action=image_to_pdf, path=图片文件路径（仅用于转换现有图片）
- Excel转PDF: action=excel_to_pdf, path=Excel文件路径（仅用于转换现有Excel）

重要规则：
- "写...保存成pdf格式" = doc_generate 或 save_document（生成新文档）
- "保存成pdf格式" 仅用于生成新文档时，不是转换现有文件
- pdf_to_word/pdf_to_image 等转换操作仅用于处理已有文件

### 10. os_agent (操作系统智能体)
- 设置音量: action=volume_set, level=0-100
- 系统关机: action=shutdown
- 系统重启: action=restart

### 11. app_agent (应用智能体)
- 打开应用: action=open, app_name=应用名称
- 关闭应用: action=close, app_name=应用名称
- 安装应用: action=install, app_name=软件名称（自动从winget安装）
- 示例: "安装剪映" -> action=install, app_name="剪映"
- 示例: "打开百度网盘"（未安装时自动安装）-> action=open, app_name="百度网盘"

### 12. download_agent (下载智能体)
- 下载文件: action=download, url=下载链接

### 13. news_agent (新闻资讯智能体)
- 获取新闻: action=fetch_news, count=数量
- 获取热点: action=fetch_hot, count=数量

### 14. screen_cast_agent (同屏智能体)
- 搜索设备: action=discover_devices
- 投屏视频: action=cast_video, video_path=本地路径

### 15. audio_decrypt_agent (音频解密智能体)
- 解密NCM文件: action=decrypt_ncm, file_path=NCM文件路径
- 支持格式: .ncm (网易云音乐), .qmc (QQ音乐), .kwm (酷我音乐)

### 16. calendar_agent (日历智能体)
- 添加日程: action=add_event, title=标题, datetime=时间
- 查询日程: action=query_events, date=日期

### 17. general (通用对话)
- 其他所有无法归类的对话
"""
    
    def _collect_keyword_mappings(self, force_reload: bool = False) -> Dict[str, tuple]:
        """从各智能体收集关键词映射（按优先级排序，优先级高的覆盖低的）"""
        if self._keyword_mappings_cache and not force_reload:
            return self._keyword_mappings_cache
        
        mappings = {}
        
        master_mappings = {
            "帮助": ("master", "help", {}),
            "功能": ("master", "help", {}),
            "你能做什么": ("master", "help", {}),
            "你会什么": ("master", "help", {}),
            "状态": ("master", "status", {}),
            "系统状态": ("master", "status", {}),
            "刷新智能体": ("master", "reload_agents", {}),
            "重新加载智能体": ("master", "reload_agents", {}),
            "热更新": ("master", "reload_agents", {}),
        }
        mappings.update(master_mappings)
        
        from ..routing.routing_manager import get_routing_manager
        routing = get_routing_manager()
        routing.reload_if_changed()
        agent_classes = routing.get_agent_classes()
        
        agents_with_priority = []
        for agent_name, class_name in agent_classes:
            try:
                module_path = f"personal_agent.agents.{agent_name}"
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name, None)
                if agent_class:
                    priority = getattr(agent_class, 'PRIORITY', 5)
                    keyword_mappings = getattr(agent_class, 'KEYWORD_MAPPINGS', {})
                    if keyword_mappings:
                        agents_with_priority.append((agent_name, priority, keyword_mappings))
                        logger.debug(f"✅ 加载 {agent_name} 关键词映射: {len(keyword_mappings)} 个")
            except Exception as e:
                logger.warning(f"加载 {agent_name} 关键词映射失败: {e}")
        
        agents_with_priority.sort(key=lambda x: x[1])
        
        for agent_name, priority, keyword_mappings in agents_with_priority:
            for keyword, (action, params) in keyword_mappings.items():
                if keyword in mappings:
                    old_agent = mappings[keyword][0]
                    logger.debug(f"关键词 '{keyword}' 从 {old_agent} 覆盖为 {agent_name} (优先级 {priority})")
                mappings[keyword] = (agent_name, action, params)
        
        self._keyword_mappings_cache = mappings
        return mappings
    
    def _replace_terms_in_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """后处理：替换参数中的关键词为实际值"""
        try:
            from .domain_knowledge import replace_terms_in_params
            return replace_terms_in_params(params, self._settings)
        except Exception as e:
            logger.debug(f"关键词替换失败: {e}")
            return params
    
    async def parse_with_llm(self, user_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """使用 LLM 解析用户意图"""
        simple_mapping = self._collect_keyword_mappings(force_reload=False)
        
        input_stripped = user_input.strip()
        punctuation = '。，！？、；：""''（）【】《》.,!?;:"\'()/'
        input_cleaned = input_stripped
        for p in punctuation:
            input_cleaned = input_cleaned.replace(p, '')
        
        if input_cleaned in ['？', '?', 'help', '帮助']:
            return "master", {"action": "help"}
        
        logger.debug(f"🔍 关键词匹配检查: '{input_stripped}' -> '{input_cleaned}', 映射数量: {len(simple_mapping)}")
        if '静音' in simple_mapping:
            logger.debug(f"🔍 '静音' 映射: {simple_mapping.get('静音')}")
        
        if input_cleaned in simple_mapping:
            agent_name, action, params = simple_mapping[input_cleaned]
            return agent_name, {"action": action, **params}
        
        if input_stripped in simple_mapping:
            agent_name, action, params = simple_mapping[input_stripped]
            return agent_name, {"action": action, **params}
        
        input_lower = input_cleaned.lower()
        for keyword, (agent_name, action, params) in simple_mapping.items():
            if keyword.lower() == input_lower:
                return agent_name, {"action": action, **params}
        
        sorted_keywords = sorted(simple_mapping.keys(), key=len, reverse=True)
        for keyword in sorted_keywords:
            agent_name, action, params = simple_mapping[keyword]
            if keyword == input_cleaned:
                return agent_name, {"action": action, **params}
        
        llm = self._get_llm_gateway()
        
        agent_capabilities = self._get_agent_capabilities()
        
        logger.debug(f"LLM 提示长度: {len(agent_capabilities)} 字符")
        
        from datetime import datetime as dt
        now = dt.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M")
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[now.weekday()]
        
        prompt = f"""你是一个意图识别助手。请根据用户的输入，识别应该由哪个智能体来处理，并提取相关参数。

当前时间：{current_date}（{weekday}）{current_time}

{agent_capabilities}

用户输入: {user_input}

请以 JSON 格式返回结果：
{{
    "agent": "智能体名称",
    "action": "操作类型",
    "params": {{}},
    "multi_step": false,
    "steps": [],
    "need_history": false,
    "history_query": {{
        "query_type": "last_file/last_contact/last_action/keyword",
        "keyword": "搜索关键词（可选）"
    }}
}}

规则：
1. 根据用户输入选择最合适的智能体
2. 提取所有相关参数
3. 如果无法确定，使用 general
4. 只返回 JSON，不要其他内容
5. 如果用户请求包含多个操作，设置 multi_step=true，并在 steps 中列出每个步骤
6. 如果用户使用代词（它、那个、他、她、刚才等）或引用之前的内容，设置 need_history=true 并指定 history_query
7. 如果用户指定了收件人（如"发送到二姐的邮箱"），必须在 params 中包含 recipient_name 参数

重要规则：
- "问大模型"、"问ai"、"和ai聊天"等 = llm_agent 的 chat，直接与 LLM 对话
- "附近"、"周边"、"周围"等位置关键词 + 店铺/餐厅/景点等 = crawler_agent 的 web_search
- 示例: "附近火锅店" -> crawler_agent, action=web_search, query="附近火锅店"
- 示例: "周边粤菜馆" -> crawler_agent, action=web_search, query="周边粤菜馆"
- 示例: "附近的厕所" -> crawler_agent, action=web_search, query="附近的厕所"
- "附件"是"附近"的错别字，应该按"附近"处理，路由到 crawler_agent
- file_agent 只处理文件系统操作（磁盘空间、搜索文件等），不处理位置搜索
- contact_agent 处理联系人管理（添加/查询/保存联系人），qq_bot_agent 只处理QQ机器人相关操作
- 示例: "老板 234566@qq.com 领导" -> contact_agent, action=add, name="老板", email="234566@qq.com", tags=["领导"]
- 示例: "保存联系人张三 13800138000" -> contact_agent, action=add, name="张三", phone="13800138000"
- 示例: "启动QQ机器人" -> qq_bot_agent, action=start

示例：
用户: "播放 三万英尺"
返回: {{"agent": "music_agent", "action": "play", "params": {{"song_name": "三万英尺"}}, "multi_step": false, "need_history": false}}

用户: "给小聪聪发一份邮件，让他明天早上过来开会"
返回: {{"agent": "email_agent", "action": "send", "params": {{"recipient_name": "小聪聪", "message": "明天早上过来开会"}}, "multi_step": false, "need_history": false}}

用户: "问大模型 什么是量子计算"
返回: {{"agent": "llm_agent", "action": "chat", "params": {{"query": "什么是量子计算"}}, "multi_step": false, "need_history": false}}

用户: "和AI聊天，帮我写一首诗"
返回: {{"agent": "llm_agent", "action": "chat", "params": {{"query": "帮我写一首诗"}}, "multi_step": false, "need_history": false}}

用户: "附件的火锅店"
返回: {{"agent": "crawler_agent", "action": "web_search", "params": {{"query": "附近火锅店"}}, "multi_step": false, "need_history": false}}

用户: "周边的厕所"
返回: {{"agent": "crawler_agent", "action": "web_search", "params": {{"query": "附近的厕所"}}, "multi_step": false, "need_history": false}}

用户: "把它转成MP3"
返回: {{"agent": "audio_decrypt_agent", "action": "decrypt_ncm", "params": {{}}, "multi_step": false, "need_history": true, "history_query": {{"query_type": "last_file"}}}}

用户: "发给他"
返回: {{"agent": "email_agent", "action": "send", "params": {{}}, "multi_step": false, "need_history": true, "history_query": {{"query_type": "last_contact"}}}}

用户: "西安三天旅游攻略"
返回: {{"agent": "travel_itinerary_agent", "action": "generate", "params": {{"destination": "西安", "days": 3}}, "multi_step": false, "need_history": false}}

用户: "写一篇北京五天的旅行攻略"
返回: {{"agent": "travel_itinerary_agent", "action": "generate", "params": {{"destination": "北京", "days": 5}}, "multi_step": false, "need_history": false}}

用户: "大同三天旅游的攻略"
返回: {{"agent": "travel_itinerary_agent", "action": "generate", "params": {{"destination": "大同", "days": 3}}, "multi_step": false, "need_history": false}}

用户: "生成一个西安三天旅游攻略的pdf，发送到我的邮箱"
返回: {{"agent": "master", "action": "workflow", "params": {{}}, "multi_step": true, "steps": [
    {{"agent": "travel_itinerary_agent", "action": "generate", "params": {{"destination": "西安", "days": 3}}}},
    {{"agent": "email_agent", "action": "send", "params": {{"attachment": "{{previous_result}}"}}}}
], "need_history": false}}

重要规则：
- 只有当用户明确要求"生成PDF并发送邮件"或"发送到邮箱"时才创建工作流
- 单纯的旅游攻略请求（如"大同三天旅游攻略"）只需要返回 travel_itinerary_agent，不要创建工作流
- 不要把简单的旅游攻略请求误解为需要生成PDF或发送邮件

用户: "把这个ncm文件转换成MP3并发邮件给我"
返回: {{"agent": "master", "action": "workflow", "params": {{}}, "multi_step": true, "steps": [
    {{"agent": "audio_decrypt_agent", "action": "decrypt_ncm", "params": {{}}}},
    {{"agent": "email_agent", "action": "send", "params": {{"attachment": "{{previous_result}}"}}}}
], "need_history": true, "history_query": {{"query_type": "last_file"}}}}

用户: "中国人寿"
返回: {{"agent": "stock_query_agent", "action": "query_stock", "params": {{"stock_code": "中国人寿"}}, "multi_step": false, "need_history": false}}

用户: "查询伊利股份股价"
返回: {{"agent": "stock_query_agent", "action": "query_stock", "params": {{"stock_code": "伊利股份"}}, "multi_step": false, "need_history": false}}

用户: "600887股票"
返回: {{"agent": "stock_query_agent", "action": "query_stock", "params": {{"stock_code": "600887"}}, "multi_step": false, "need_history": false}}

用户: "今天大盘怎么样"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "大盘"}}, "multi_step": false, "need_history": false}}

用户: "大盘指数"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "大盘"}}, "multi_step": false, "need_history": false}}

用户: "大盘行情"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "大盘"}}, "multi_step": false, "need_history": false}}

用户: "深证成指"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "深证成指"}}, "multi_step": false, "need_history": false}}

用户: "上证指数"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "上证指数"}}, "multi_step": false, "need_history": false}}

用户: "创业板"
返回: {{"agent": "stock_query_agent", "action": "query_index", "params": {{"index_name": "创业板指"}}, "multi_step": false, "need_history": false}}
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            
            history_tools = self._get_history_search_tools()
            
            response = await llm.chat(messages, tools=history_tools)
            
            if response.usage:
                prompt_tokens = response.usage.get("prompt_tokens", 0)
                completion_tokens = response.usage.get("completion_tokens", 0)
                total_tokens = response.usage.get("total_tokens", 0)
                logger.info(f"📊 Token 统计: 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
                try:
                    from ..utils.token_counter import update_token_count
                    update_token_count(total_tokens)
                except Exception:
                    pass
            
            if response.tool_calls:
                logger.info(f"LLM 请求调用工具: {[tc.name for tc in response.tool_calls]}")
                
                tool_results = await self._handle_tool_calls(response.tool_calls)
                
                messages.append({"role": "assistant", "content": response.content or "", "tool_calls": [
                    {"id": tc.id, "function": {"name": tc.name, "arguments": tc.arguments}}
                    for tc in response.tool_calls
                ]})
                
                for tool_result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result["tool_call_id"],
                        "content": tool_result["content"]
                    })
                
                response = await llm.chat(messages, tools=history_tools)
                
                if response.usage:
                    prompt_tokens = response.usage.get("prompt_tokens", 0)
                    completion_tokens = response.usage.get("completion_tokens", 0)
                    total_tokens = response.usage.get("total_tokens", 0)
                    logger.info(f"📊 Token 统计(工具调用后): 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
                    try:
                        from ..utils.token_counter import update_token_count
                        update_token_count(total_tokens)
                    except Exception:
                        pass
            
            result = json.loads(response.content.strip().replace("```json", "").replace("```", "").strip())
            agent = result.get("agent", "general")
            action = result.get("action", "")
            params = result.get("params", {})
            multi_step = result.get("multi_step", False)
            steps = result.get("steps", [])
            need_history = result.get("need_history", False)
            history_query = result.get("history_query", {})
            
            if need_history and history_query and not response.tool_calls:
                query_type = history_query.get("query_type")
                keyword = history_query.get("keyword")
                
                if query_type:
                    from ..channels.conversation_manager import conversation_manager
                    history_result = conversation_manager.search_history(query_type, keyword)
                    
                    if history_result.get("found"):
                        history_data = history_result.get("result", {})
                        
                        if query_type == "last_file" and "file_path" in history_data:
                            file_path = history_data["file_path"]
                            from pathlib import Path
                            ext = Path(file_path).suffix.lower()
                            
                            agent_file_types = {
                                "music_agent": [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac", ".ncm"],
                                "video_agent": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
                                "document_agent": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".png", ".jpg", ".jpeg"],
                                "file_agent": [".txt", ".csv", ".json", ".xml"],
                                "developer_agent": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"],
                                "audio_decrypt_agent": [".ncm", ".qmc", ".kwm"],
                            }
                            
                            allowed_types = agent_file_types.get(agent, [])
                            if not allowed_types or ext in allowed_types:
                                params["file_path"] = file_path
                                logger.info(f"从历史获取文件: {file_path}")
                            else:
                                logger.info(f"历史文件类型不匹配: {ext} 不在 {agent} 支持的类型中")
                        
                        elif query_type == "last_contact":
                            if "email" in history_data:
                                params["to"] = history_data["email"]
                            elif "name" in history_data:
                                params["recipient_name"] = history_data["name"]
                            logger.info(f"从历史获取联系人: {history_data}")
            
            if agent != "general":
                params["action"] = action
            
            params["original_text"] = user_input
            
            params = self._replace_terms_in_params(params)
            
            if multi_step and steps:
                for step in steps:
                    if "params" in step:
                        step["params"] = self._replace_terms_in_params(step["params"])
                params["multi_step"] = True
                params["steps"] = steps
                intent_type = "workflow"
                logger.info(f"LLM 解析多步骤意图: steps={len(steps)}")
            else:
                intent_type = self._agent_to_intent_type(agent)
                if agent == "stock_query_agent" and action == "query_index":
                    intent_type = "query_index"
                    logger.info(f"🎯 股票智能体指数查询，设置意图类型: query_index")
            
            logger.info(f"LLM 解析意图: agent={agent}, action={action}, intent_type={intent_type}, params={params}")
            return intent_type, params
            
        except Exception as e:
            logger.error(f"LLM 解析意图失败: {e}")
            return IntentType.GENERAL, None
    
    def _get_history_search_tools(self) -> List:
        """获取历史查询工具定义"""
        from ..llm.base import ToolDefinition
        
        return [
            ToolDefinition(
                name="search_conversation_history",
                description="搜索对话历史，查找用户之前提到的文件、联系人、操作等。当用户使用代词（它、那个、刚才）或引用之前的内容时使用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["last_file", "last_contact", "last_action", "keyword"],
                            "description": "查询类型: last_file=最近文件, last_contact=最近联系人, last_action=最近操作, keyword=关键词搜索"
                        },
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词（当query_type为keyword时必填）"
                        }
                    },
                    "required": ["query_type"]
                }
            )
        ]
    
    async def _handle_tool_calls(self, tool_calls: List) -> List[Dict]:
        """处理工具调用"""
        results = []
        
        for tool_call in tool_calls:
            if tool_call.name == "search_conversation_history":
                try:
                    args = json.loads(tool_call.arguments) if isinstance(tool_call.arguments, str) else tool_call.arguments
                    query_type = args.get("query_type")
                    keyword = args.get("keyword")
                    
                    from ..channels.conversation_manager import conversation_manager
                    result = conversation_manager.search_history(query_type, keyword)
                    
                    results.append({
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
                    logger.info(f"历史查询: type={query_type}, keyword={keyword}, found={result.get('found')}")
                    
                except Exception as e:
                    logger.error(f"工具调用失败: {e}")
                    results.append({
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"found": False, "error": str(e)}, ensure_ascii=False)
                    })
            else:
                results.append({
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"error": f"未知工具: {tool_call.name}"}, ensure_ascii=False)
                })
        
        return results
    
    def _agent_to_intent_type(self, agent: str) -> str:
        """将智能体名称转换为意图类型"""
        agent_lower = agent.lower()
        
        from ..routing.routing_manager import get_routing_manager
        routing = get_routing_manager()
        agent_to_intent = routing.get_agent_to_intent()
        
        intent_type = agent_to_intent.get(agent_lower)
        if intent_type:
            return intent_type
        
        fallback_mapping = {
            "audio_decrypt_agent": "audio_decrypt",
            "general": IntentType.GENERAL,
        }
        return fallback_mapping.get(agent_lower, IntentType.GENERAL)

    async def _analyze_missing_skill_with_llm(self, user_input: str, file_ext: str = None) -> Optional[Dict[str, Any]]:
        """使用 LLM 分析是否需要创建新技能"""
        llm = self._get_llm_gateway()
        
        existing_agents = self._get_existing_agent_names()
        
        prompt = f"""分析用户请求，判断处理方式。

已有智能体: {', '.join(existing_agents)}

用户请求: {user_input}
文件类型: {file_ext or '无'}

请判断：
1. 这个请求你（LLM）能否直接回答处理？
   - 以下类型的问题 LLM 可以直接回答：
     * 基础知识问题（如：西安有多少个区、中国的首都是哪里、地球的半径是多少）
     * 概念解释（如：什么是人工智能、什么是区块链）
     * 闲聊（如：你好、讲个笑话）
     * 翻译（如：把这句话翻译成英文）
     * 总结（如：总结这段文字）
     * 一般性建议（如：如何学习编程、如何保持健康）
   
   - 以下类型的问题需要创建新技能：
     * 需要实时数据（如：今天天气、当前股票价格、最新新闻）
     * 需要特定工具（如：播放音乐、发送邮件、生成图片）
     * 需要访问外部系统（如：打开应用、控制智能家居）
     * 需要文件操作（如：下载文件、转换文档格式）

2. 如果需要特定工具、数据源、或外部 API 才能处理，才需要创建新技能

返回 JSON 格式：
{{
    "llm_can_handle": true/false,
    "need_new_skill": true/false,
    "agent_name": "建议的智能体名称（如需要，使用 snake_case 命名）",
    "skill_name": "技能显示名称",
    "skill_description": "技能描述（一句话概括）",
    "detailed_description": "详细功能描述（说明这个智能体需要实现什么功能）",
    "trigger_keywords": ["触发关键词列表"],
    "suggested_actions": [
        {{
            "name": "操作名称",
            "description": "操作描述",
            "params": ["参数列表"],
            "examples": ["示例请求"]
        }}
    ],
    "required_dependencies": ["需要的 Python 库"],
    "external_apis": ["需要的外部 API"],
    "data_sources": ["需要的数据源"],
    "implementation_notes": ["实现注意事项"],
    "edge_cases": ["边缘情况处理"],
    "priority": "high/medium/low"
}}

规则：
- 如果 llm_can_handle 为 true，返回 {{"llm_can_handle": true, "need_new_skill": false}}
- 只有需要工具/数据/API 时，才设置 need_new_skill 为 true
- 尽可能详细地填写所有字段，这些信息将用于生成开发文档
- 基础地理知识、历史知识、科学知识等不需要创建技能"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            result = json.loads(response.content.strip().replace("```json", "").replace("```", "").strip())
            
            if result.get("llm_can_handle"):
                logger.debug(f"LLM 可以直接处理: {user_input}")
                return None
            
            if result.get("need_new_skill"):
                return {
                    "agent_name": result.get("agent_name", "new_agent"),
                    "skill_name": result.get("skill_name", result.get("agent_name", "新技能")),
                    "skill_description": result.get("skill_description", ""),
                    "detailed_description": result.get("detailed_description", ""),
                    "trigger_keywords": result.get("trigger_keywords", []),
                    "suggested_actions": result.get("suggested_actions", []),
                    "required_dependencies": result.get("required_dependencies", []),
                    "external_apis": result.get("external_apis", []),
                    "data_sources": result.get("data_sources", []),
                    "implementation_notes": result.get("implementation_notes", []),
                    "edge_cases": result.get("edge_cases", []),
                    "priority": result.get("priority", "medium"),
                    "user_request": user_input
                }
            
            return None
            
        except Exception as e:
            logger.error(f"分析缺失技能失败: {e}")
            return None
    
    def _get_existing_agent_names(self) -> List[str]:
        """获取已有智能体名称列表"""
        try:
            from ..agents.agent_scanner import get_agent_scanner
            scanner = get_agent_scanner()
            agents_info = scanner.get_all_agents_info()
            return [info.get('name', '') for info in agents_info if info.get('name')]
        except Exception as e:
            logger.debug(f"获取智能体列表失败: {e}")
            return ["music_agent", "email_agent", "weather_agent", "contact_agent", 
                    "file_agent", "crawler_agent", "developer_agent", "document_agent",
                    "os_agent", "app_agent", "download_agent", "news_agent", 
                    "video_agent", "calendar_agent", "tts_agent"]

    def parse(self, user_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        解析用户意图 - 同步接口，内部调用异步方法
        
        Returns:
            (intent_type, params)
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.parse_with_llm(user_input)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.parse_with_llm(user_input))
        except Exception as e:
            logger.error(f"解析意图失败: {e}")
            return IntentType.GENERAL, None

    async def parse_async(self, user_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        异步解析用户意图
        
        Returns:
            (intent_type, params)
        """
        return await self.parse_with_llm(user_input)

    def _get_agent_help(self, agent_name: str) -> str:
        """从 Skill 文件获取智能体的帮助信息"""
        try:
            from pathlib import Path
            
            agents_dir = Path(__file__).parent.parent / "agents"
            skill_file = agents_dir / f"{agent_name}.md"
            
            if skill_file.exists():
                content = skill_file.read_text(encoding='utf-8')
                
                lines = content.split('\n')
                
                name = ""
                description = ""
                when_to_use = []
                actions = []
                action_descriptions = {}
                
                in_frontmatter = False
                in_when_to_use = False
                in_how_to_use = False
                current_action = None
                
                for line in lines:
                    stripped = line.strip()
                    
                    if stripped == '---':
                        in_frontmatter = not in_frontmatter
                        continue
                    
                    if in_frontmatter:
                        if stripped.startswith('name:'):
                            name = stripped[5:].strip()
                        elif stripped.startswith('description:'):
                            description = stripped[12:].strip()
                        continue
                    
                    if stripped.startswith('## When to use'):
                        in_when_to_use = True
                        continue
                    elif stripped.startswith('## How to use'):
                        in_when_to_use = False
                        in_how_to_use = True
                        continue
                    elif stripped.startswith('## Edge cases'):
                        in_how_to_use = False
                        continue
                    elif stripped.startswith('## '):
                        in_when_to_use = False
                        in_how_to_use = False
                        continue
                    
                    if in_when_to_use and stripped.startswith('- '):
                        when_to_use.append(stripped[2:])
                    
                    if in_how_to_use:
                        if stripped.startswith('### '):
                            current_action = stripped[4:].strip()
                            if current_action:
                                actions.append(current_action)
                        elif current_action and stripped and not stripped.startswith('-') and not stripped.startswith('示例'):
                            if current_action not in action_descriptions:
                                action_descriptions[current_action] = stripped
                
                emoji_map = {
                    "music": "🎵",
                    "video": "🎬",
                    "email": "📧",
                    "weather": "🌤️",
                    "contact": "📇",
                    "file": "📁",
                    "crawler": "🕷️",
                    "developer": "💻",
                    "pdf": "📄",
                    "os": "🖥️",
                    "app": "📱",
                    "download": "⬇️",
                    "news": "📰",
                    "screen_cast": "📺",
                    "calendar": "📅",
                }
                
                emoji = ""
                for key, em in emoji_map.items():
                    if key in agent_name:
                        emoji = em
                        break
                
                help_lines = []
                help_lines.append(f"{emoji} {name or agent_name} - {description}")
                help_lines.append("")
                
                if when_to_use:
                    help_lines.append("触发场景：")
                    for item in when_to_use[:5]:
                        help_lines.append(f"• {item}")
                
                if actions:
                    help_lines.append("")
                    help_lines.append("支持操作：")
                    for action in actions[:6]:
                        desc = action_descriptions.get(action, "")
                        if desc:
                            help_lines.append(f"• {action}: {desc}")
                        else:
                            help_lines.append(f"• {action}")
                
                help_lines.append("")
                help_lines.append(f"详细信息请查看 {agent_name}.md")
                
                return '\n'.join(help_lines)
            
        except Exception as e:
            logger.warning(f"从 Skill 文件获取帮助信息失败: {e}")
        
        return f"暂无 {agent_name} 的帮助信息，请查看 {agent_name}.md 文件"


intent_parser = IntentParser()
