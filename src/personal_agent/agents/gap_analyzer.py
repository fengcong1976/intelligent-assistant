"""
能力缺口分析器
分析系统缺少的智能体能力，并生成建议
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import Counter
from loguru import logger


class CapabilityGapAnalyzer:
    """
    能力缺口分析器
    
    功能：
    1. 记录未处理的用户请求
    2. 分析请求模式，找出常见需求
    3. 生成智能体建议
    """
    
    INSTANCE = None
    
    def __new__(cls, *args, **kwargs):
        if cls.INSTANCE is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE
    
    def __init__(self, data_dir: Optional[Path] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.data_dir = data_dir or Path.home() / ".personal_agent" / "analytics"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.unhandled_file = self.data_dir / "unhandled_requests.json"
        self.suggestions_file = self.data_dir / "agent_suggestions.json"
        
        self.unhandled_requests: List[Dict] = self._load_unhandled()
        self.agent_suggestions: List[Dict] = self._load_suggestions()
        
        self._initialized = True
        logger.info(f"📊 能力缺口分析器已初始化，已记录 {len(self.unhandled_requests)} 条未处理请求")
    
    def _load_unhandled(self) -> List[Dict]:
        """加载未处理请求记录"""
        if self.unhandled_file.exists():
            try:
                with open(self.unhandled_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载未处理请求记录失败: {e}")
        return []
    
    def _save_unhandled(self):
        """保存未处理请求记录"""
        try:
            with open(self.unhandled_file, 'w', encoding='utf-8') as f:
                json.dump(self.unhandled_requests[-500:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存未处理请求记录失败: {e}")
    
    def _load_suggestions(self) -> List[Dict]:
        """加载智能体建议"""
        if self.suggestions_file.exists():
            try:
                with open(self.suggestions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载智能体建议失败: {e}")
        return []
    
    def _save_suggestions(self):
        """保存智能体建议"""
        try:
            with open(self.suggestions_file, 'w', encoding='utf-8') as f:
                json.dump(self.agent_suggestions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存智能体建议失败: {e}")
    
    def record_unhandled(
        self, 
        user_input: str, 
        intent_type: str = "GENERAL",
        matched_keywords: List[str] = None,
        context: Dict = None
    ):
        """
        记录未处理的用户请求
        
        Args:
            user_input: 用户输入
            intent_type: 意图类型（通常是 GENERAL）
            matched_keywords: 匹配到的关键词
            context: 上下文信息
        """
        record = {
            "input": user_input,
            "intent_type": intent_type,
            "matched_keywords": matched_keywords or [],
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        
        self.unhandled_requests.append(record)
        self._save_unhandled()
        
        logger.debug(f"📝 记录未处理请求: {user_input[:50]}...")
    
    def analyze_patterns(self, days: int = 7) -> Dict[str, Any]:
        """
        分析未处理请求的模式
        
        Args:
            days: 分析最近几天的数据
            
        Returns:
            分析结果
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        recent_requests = [
            r for r in self.unhandled_requests 
            if r.get("date", "") >= cutoff_date
        ]
        
        if not recent_requests:
            return {
                "total": 0,
                "patterns": [],
                "keywords": [],
                "suggestions": []
            }
        
        keyword_counter = Counter()
        action_counter = Counter()
        domain_counter = Counter()
        
        action_patterns = {
            "翻译": ["翻译", "translate", "译成", "英文", "中文", "日文"],
            "记账": ["记账", "账单", "支出", "收入", "花销", "消费"],
            "闹钟": ["闹钟", "定时", "提醒我", "分钟后", "小时后"],
            "笔记": ["笔记", "记一下", "备忘", "便签", "记事"],
            "购物": ["购物", "买", "下单", "订单", "淘宝", "京东"],
            "导航": ["导航", "路线", "怎么走", "地图", "定位"],
            "股票": ["股票", "基金", "行情", "涨跌", "投资"],
            "图片处理": ["图片", "修图", "P图", "抠图", "压缩图片"],
            "语音": ["语音", "朗读", "TTS", "说"],
            "聊天": ["聊天", "陪我聊", "无聊"],
            "健康": ["健康", "运动", "步数", "卡路里", "健身"],
            "学习": ["学习", "教程", "课程", "教学"],
            "游戏": ["游戏", "玩", "娱乐"],
            "格式转换": ["转换成", "转成", "格式转换", "转换格式", "转码"],
            "解密": ["解密", "破解", "ncm", "qmc", "kwm"],
            "压缩": ["压缩", "解压", "zip", "rar", "7z"],
            "OCR": ["识别文字", "图片转文字", "OCR", "提取文字"],
        }
        
        domain_keywords = {
            "翻译": ["翻译", "translate", "英文", "中文", "日文", "韩文"],
            "财务": ["记账", "账单", "支出", "收入", "花销", "消费", "钱"],
            "时间管理": ["闹钟", "定时", "倒计时", "提醒我"],
            "笔记": ["笔记", "记一下", "备忘", "便签", "记事"],
            "购物": ["购物", "买", "下单", "订单", "淘宝", "京东"],
            "导航": ["导航", "路线", "怎么走", "地图", "定位", "去"],
            "金融": ["股票", "基金", "行情", "涨跌", "投资"],
            "图像": ["图片", "修图", "P图", "抠图", "照片"],
            "语音": ["语音", "朗读", "TTS", "说", "听"],
            "社交": ["聊天", "陪我聊", "无聊", "朋友"],
            "健康": ["健康", "运动", "步数", "卡路里", "健身"],
            "教育": ["学习", "教程", "课程", "教学", "知识"],
            "娱乐": ["游戏", "玩", "娱乐", "笑话"],
            "格式转换": ["转换成", "转成", "格式转换", "转换格式", "转码", "mp3", "mp4", "wav", "flac"],
            "解密": ["解密", "破解", "ncm", "qmc", "kwm", "加密"],
            "压缩": ["压缩", "解压", "zip", "rar", "7z", "tar"],
            "OCR": ["识别文字", "图片转文字", "OCR", "提取文字", "文字识别"],
        }
        
        for request in recent_requests:
            input_text = request.get("input", "").lower()
            
            for action, keywords in action_patterns.items():
                if any(kw in input_text for kw in keywords):
                    action_counter[action] += 1
            
            for domain, keywords in domain_keywords.items():
                if any(kw in input_text for kw in keywords):
                    domain_counter[domain] += 1
            
            for word in input_text.split():
                if len(word) >= 2:
                    keyword_counter[word] += 1
        
        suggestions = self._generate_suggestions(action_counter, domain_counter)
        
        return {
            "total": len(recent_requests),
            "period_days": days,
            "top_actions": action_counter.most_common(10),
            "top_domains": domain_counter.most_common(10),
            "top_keywords": keyword_counter.most_common(20),
            "suggestions": suggestions,
        }
    
    def _generate_suggestions(
        self, 
        action_counter: Counter, 
        domain_counter: Counter
    ) -> List[Dict]:
        """
        生成智能体建议
        
        Args:
            action_counter: 操作计数
            domain_counter: 领域计数
            
        Returns:
            智能体建议列表
        """
        suggestions = []
        
        agent_templates = {
            "翻译": {
                "name": "translator_agent",
                "description": "翻译智能体 - 支持多语言翻译",
                "capabilities": ["translate_text", "detect_language", "batch_translate"],
                "priority": "high",
                "reason": "用户频繁请求翻译功能",
            },
            "财务": {
                "name": "finance_agent",
                "description": "财务智能体 - 记账和财务管理",
                "capabilities": ["record_expense", "record_income", "query_balance", "generate_report"],
                "priority": "high",
                "reason": "用户需要记账和财务管理功能",
            },
            "时间管理": {
                "name": "alarm_agent",
                "description": "闹钟智能体 - 定时提醒",
                "capabilities": ["set_alarm", "set_timer", "list_alarms", "cancel_alarm"],
                "priority": "medium",
                "reason": "用户需要定时提醒功能",
            },
            "笔记": {
                "name": "note_agent",
                "description": "笔记智能体 - 笔记和备忘录管理",
                "capabilities": ["create_note", "search_notes", "delete_note", "list_notes"],
                "priority": "medium",
                "reason": "用户需要记录笔记和备忘",
            },
            "购物": {
                "name": "shopping_agent",
                "description": "购物智能体 - 在线购物助手",
                "capabilities": ["search_product", "track_order", "compare_price"],
                "priority": "low",
                "reason": "用户有购物相关需求",
            },
            "导航": {
                "name": "navigation_agent",
                "description": "导航智能体 - 地图和路线规划",
                "capabilities": ["get_route", "search_location", "get_traffic"],
                "priority": "medium",
                "reason": "用户需要导航和路线规划",
            },
            "金融": {
                "name": "stock_agent",
                "description": "股票智能体 - 股票和基金查询",
                "capabilities": ["query_stock", "query_fund", "get_portfolio"],
                "priority": "low",
                "reason": "用户关注金融投资",
            },
            "图像": {
                "name": "image_agent",
                "description": "图像智能体 - 图片处理",
                "capabilities": ["resize_image", "compress_image", "convert_format", "edit_image"],
                "priority": "low",
                "reason": "用户需要图片处理功能",
            },
            "语音": {
                "name": "tts_agent",
                "description": "语音智能体 - 文字转语音",
                "capabilities": ["text_to_speech", "set_voice", "set_speed"],
                "priority": "low",
                "reason": "用户需要语音合成功能",
            },
            "社交": {
                "name": "chat_agent",
                "description": "聊天智能体 - 日常对话陪伴",
                "capabilities": ["chat", "tell_joke", "recommend"],
                "priority": "low",
                "reason": "用户需要聊天陪伴",
            },
            "健康": {
                "name": "health_agent",
                "description": "健康智能体 - 健康和运动管理",
                "capabilities": ["track_exercise", "count_calories", "health_tips"],
                "priority": "medium",
                "reason": "用户关注健康和运动",
            },
            "教育": {
                "name": "education_agent",
                "description": "教育智能体 - 学习和教程",
                "capabilities": ["search_course", "explain_concept", "quiz"],
                "priority": "low",
                "reason": "用户有学习需求",
            },
            "娱乐": {
                "name": "game_agent",
                "description": "游戏智能体 - 小游戏和娱乐",
                "capabilities": ["play_game", "tell_joke", "riddle"],
                "priority": "low",
                "reason": "用户需要娱乐功能",
            },
            "格式转换": {
                "name": "converter_agent",
                "description": "格式转换智能体 - 音视频格式转换",
                "capabilities": ["convert_audio", "convert_video", "batch_convert"],
                "priority": "high",
                "reason": "用户需要文件格式转换功能",
            },
            "解密": {
                "name": "decrypt_agent",
                "description": "解密智能体 - 加密文件解密（如网易云ncm、QQ音乐qmc）",
                "capabilities": ["decrypt_ncm", "decrypt_qmc", "decrypt_kwm"],
                "priority": "high",
                "reason": "用户需要解密加密的音乐文件",
            },
            "压缩": {
                "name": "archive_agent",
                "description": "压缩智能体 - 文件压缩和解压",
                "capabilities": ["compress_files", "extract_archive", "list_archive"],
                "priority": "medium",
                "reason": "用户需要文件压缩和解压功能",
            },
            "OCR": {
                "name": "ocr_agent",
                "description": "OCR智能体 - 图片文字识别",
                "capabilities": ["recognize_text", "extract_text", "batch_ocr"],
                "priority": "medium",
                "reason": "用户需要从图片中提取文字",
            },
        }
        
        for domain, count in domain_counter.most_common(10):
            if count >= 3 and domain in agent_templates:
                template = agent_templates[domain]
                suggestion = {
                    **template,
                    "request_count": count,
                    "confidence": min(count / 10, 1.0),
                }
                
                existing = next(
                    (s for s in self.agent_suggestions if s["name"] == suggestion["name"]),
                    None
                )
                
                if existing:
                    existing["request_count"] = count
                    existing["last_suggested"] = datetime.now().isoformat()
                else:
                    suggestion["first_suggested"] = datetime.now().isoformat()
                    suggestion["last_suggested"] = datetime.now().isoformat()
                    self.agent_suggestions.append(suggestion)
                
                suggestions.append(suggestion)
        
        if suggestions:
            self._save_suggestions()
        
        return suggestions
    
    def get_missing_agents_report(self) -> str:
        """
        获取缺失智能体报告
        
        Returns:
            格式化的报告文本
        """
        analysis = self.analyze_patterns(days=30)
        
        if analysis["total"] == 0:
            return "📊 系统运行良好，暂无缺失智能体的建议。"
        
        lines = []
        lines.append("📊 智能体缺口分析报告")
        lines.append("=" * 40)
        lines.append(f"📈 最近30天未处理请求: {analysis['total']} 条")
        lines.append("")
        
        if analysis["top_domains"]:
            lines.append("🔍 高频需求领域:")
            for domain, count in analysis["top_domains"][:5]:
                lines.append(f"   • {domain}: {count} 次")
            lines.append("")
        
        if analysis["suggestions"]:
            lines.append("💡 建议添加的智能体:")
            for sug in analysis["suggestions"][:5]:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sug["priority"], "⚪")
                lines.append(f"   {priority_emoji} {sug['name']}")
                lines.append(f"      描述: {sug['description']}")
                lines.append(f"      需求次数: {sug['request_count']}")
                lines.append(f"      原因: {sug['reason']}")
                lines.append("")
        else:
            lines.append("💡 暂无明确建议，继续收集数据中...")
        
        return "\n".join(lines)
    
    def clear_old_records(self, days: int = 90):
        """清理旧记录"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        original_count = len(self.unhandled_requests)
        
        self.unhandled_requests = [
            r for r in self.unhandled_requests 
            if r.get("date", "") >= cutoff_date
        ]
        
        if len(self.unhandled_requests) < original_count:
            self._save_unhandled()
            logger.info(f"🧹 清理了 {original_count - len(self.unhandled_requests)} 条旧记录")


def get_gap_analyzer() -> CapabilityGapAnalyzer:
    """获取能力缺口分析器实例"""
    return CapabilityGapAnalyzer()
