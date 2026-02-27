from loguru import logger
from typing import Dict, Any, Optional, List
from ..base import BaseAgent, Task
from .tts_player import TTSPlayer
from ..email_agent import EmailAgent
import tempfile
import os
import asyncio
import re

class TTSAgent(BaseAgent):
    PRIORITY: int = 1
    
    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "语音合成": ("synthesize", {}),
        "转语音": ("synthesize", {}),
        "文字转语音": ("synthesize", {}),
        "TTS": ("synthesize", {}),
        "朗读": ("synthesize", {}),
        "合成语音": ("synthesize", {}),
        "生成音频": ("synthesize", {}),
        "转成音频": ("synthesize", {}),
        "合成MP3": ("synthesize", {}),
        "合成音频": ("synthesize", {}),
        "发到我邮箱": ("synthesize_and_send", {}),
        "有哪些音色": ("list_voices", {}),
        "语音合成有哪些声音": ("list_voices", {}),
        "切换音色": ("list_voices", {}),
        "更换音色": ("list_voices", {}),
        "设置音色": ("list_voices", {}),
    }
    
    AVAILABLE_VOICES = {
        "longyue_v3": "龙悦v3 (活力女声)",
        "longfei_v3": "龙飞v3 (磁性男声)",
        "longshuo_v3": "龙硕v3 (沉稳男声)",
        "longyingjing_v3": "龙盈京v3 (京味女声)",
        "longjielidou_v3": "龙杰力豆v3 (童声)",
    }
    
    def __init__(self):
        super().__init__(name="tts_agent", description="将文本转换为语音音频文件，支持多种音色和格式输出")
        
        self.register_capability(
            capability="tts_speak",
            description="文字转语音。将文本转换为语音播放。",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要朗读的文本内容"
                    }
                },
                "required": ["text"]
            },
            category="tts"
        )
        
        # 使用独立的 TTSPlayer，与系统消息的发声完全分开
        self.tts_player = TTSPlayer()
        logger.info("TTSAgent: Initialized with independent TTSPlayer")
    
    async def execute_task(self, task: Task) -> Any:
        if task.type == "action":
            return await self._handle_action(task.params)
        elif task.type in ("tts_speak", "synthesize_and_play", "text_to_speech"):
            return await self._synthesize_and_play(task.params)
        elif task.type == "synthesize":
            return await self._synthesize(task.params)
        elif task.type == "synthesize_and_send":
            return await self._synthesize_and_send(task.params)
        elif task.type == "list_voices":
            return self._list_voices()
        elif task.type == "agent_help":
            return self._get_help_info()
        elif task.type == "general":
            text = task.params.get("text", task.content or "")
            if not text:
                return self.cannot_handle("未提供文本内容")
            # 解析音色参数并清理文本
            voice, cleaned_text = self._parse_voice_from_text(text)
            return await self._synthesize_and_play({"text": cleaned_text, "voice": voice})
        return self.cannot_handle("未知操作")
    
    def _parse_voice_from_text(self, text: str) -> tuple:
        """从文本中解析音色参数并清理文本
        
        支持的格式：
        - 使用音色 longyue_v3
        - 用龙悦v3的声音
        - 用童声朗读
        - 换成男声
        
        Returns:
            tuple: (voice_code, cleaned_text)
        """
        text_lower = text.lower()
        cleaned_text = text
        voice_code = "longyue_v3"  # 默认音色
        
        # 定义音色关键词映射
        voice_keywords = {
            "longyue_v3": ["longyue_v3", "龙悦", "活力女声", "女声"],
            "longfei_v3": ["longfei_v3", "龙飞", "磁性男声", "男声"],
            "longshuo_v3": ["longshuo_v3", "龙硕", "沉稳男声"],
            "longyingjing_v3": ["longyingjing_v3", "龙盈京", "京味女声", "京味"],
            "longjielidou_v3": ["longjielidou_v3", "龙杰力豆", "童声", "儿童", "小孩"],
        }
        
        # 定义需要移除的模式
        remove_patterns = [
            r"使用音色[:：]\s*",
            r"使用音色\s+",
            r"用音色[:：]\s*",
            r"用音色\s+",
            r"音色[:：]\s*",
            r"音色\s+",
            r"切换音色[:：]\s*",
            r"切换音色\s+",
            r"更换音色[:：]\s*",
            r"更换音色\s+",
            r"设置音色[:：]\s*",
            r"设置音色\s+",
            r"换成",
            r"用",
            r"的声音",
            r"朗读",
        ]
        
        # 首先尝试匹配音色代码
        for voice, keywords in voice_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    voice_code = voice
                    # 从文本中移除音色关键词
                    cleaned_text = re.sub(re.escape(keyword), "", cleaned_text, flags=re.IGNORECASE)
                    break
            if voice_code != "longyue_v3":
                break
        
        # 移除音色设置相关的模式
        for pattern in remove_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # 清理多余的空格
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
        
        return voice_code, cleaned_text
    
    async def _handle_action(self, params: Dict) -> str:
        action = params.get("action")
        if not action:
            return self.cannot_handle("未指定操作类型")
        
        try:
            if action == "synthesize":
                return await self._synthesize(params)
            elif action == "synthesize_and_play":
                return await self._synthesize_and_play(params)
            elif action == "synthesize_and_send":
                return await self._synthesize_and_send(params)
            elif action == "list_voices":
                return self._list_voices()
            else:
                return self.cannot_handle(f"不支持的操作: {action}")
        except Exception as e:
            logger.exception(f"TTS action failed: {e}")
            return f"❌ 合成失败: {str(e)}"
    
    async def _synthesize(self, params: Dict) -> str:
        text = params.get("text", "").strip()
        if not text:
            return self.cannot_handle("文本内容不能为空")
        
        output_path = params.get("output_path")
        voice = params.get("voice", "longyue_v3")
        
        if voice not in self.AVAILABLE_VOICES:
            return self.cannot_handle(f"不支持的音色: {voice}。可用音色: {', '.join(self.AVAILABLE_VOICES.keys())}")
        
        try:
            result_path = await self.tts_player.synthesize_to_file(
                text=text,
                output_path=output_path,
                voice=voice,
            )
            if result_path:
                return f"✅ 已生成音频文件: {result_path}"
            else:
                return "❌ 语音合成失败，请检查API配置"
        except Exception as e:
            logger.exception(f"TTS synthesize failed: {e}")
            raise e
    
    async def _synthesize_and_play(self, params: Dict) -> str:
        text = params.get("text", "").strip()
        if not text:
            return self.cannot_handle("文本内容不能为空")
        
        voice = params.get("voice", "longyue_v3")
        if voice not in self.AVAILABLE_VOICES:
            return self.cannot_handle(f"不支持的音色: {voice}")
        
        try:
            # 先合成到文件
            output_path = await self.tts_player.synthesize_to_file(text, voice=voice)
            if not output_path:
                return "❌ 语音合成失败，请检查API配置"
            
            # 然后播放
            success = await self.tts_player._play_audio(output_path)
            if success:
                voice_name = self.AVAILABLE_VOICES.get(voice, voice)
                return f"✅ 已合成并播放语音\n\n📝 文件路径: {output_path}\n🎙️ 使用音色: {voice_name}"
            else:
                return f"⚠️ 语音合成成功，但播放失败\n\n📝 文件路径: {output_path}"
        except Exception as e:
            logger.exception(f"TTS synthesize_and_play failed: {e}")
            raise e
    
    async def _synthesize_and_send(self, params: Dict) -> str:
        text = params.get("text", "").strip()
        if not text:
            return self.cannot_handle("文本内容不能为空")
        
        recipient = params.get("recipient")
        if not recipient:
            return self.cannot_handle("收件人邮箱未指定，请提供邮箱地址")
        
        voice = params.get("voice", "longyue_v3")
        if voice not in self.AVAILABLE_VOICES:
            return self.cannot_handle(f"不支持的音色: {voice}")
        
        try:
            result_path = await self.tts_player.synthesize_to_file(
                text=text,
                voice=voice,
            )
            if not result_path:
                return "❌ 语音合成失败，请检查API配置"
        except Exception as e:
            logger.exception(f"TTS synthesize failed: {e}")
            raise e
        
        try:
            email_agent = EmailAgent()
            await email_agent.send_email(
                recipient=recipient,
                subject="TTS语音合成结果",
                body="请查收附件中的语音文件。",
                attachments=[result_path]
            )
            return f"✅ 已发送到 {recipient}"
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            raise e
    
    def _list_voices(self) -> str:
        voices_list = "\n".join([f"- {k}: {v}" for k, v in self.AVAILABLE_VOICES.items()])
        return f"✅ 可用音色:\n{voices_list}"
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 语音合成智能体

### 功能说明
语音合成智能体可以将文本转换为语音音频文件，支持多种音色和格式输出。

### 支持的操作
- **语音合成**：将文本转换为语音文件
- **语音播放**：合成并播放语音
- **发送邮件**：合成语音并发送到邮箱
- **查看音色**：列出所有可用音色
- **设置音色**：切换不同的声音

### 使用示例
- "语音合成 今天天气真好" - 将文本转换为语音文件
- "文字转语音 你好世界" - 将文本转换为语音文件
- "朗读 这是一段测试文本" - 将文本转换为语音文件
- "有哪些音色" - 查看所有可用音色
- "语音合成 今天天气真好 发到我邮箱" - 合成语音并发送到邮箱

### 支持的音色
- longyue_v3: 龙悦v3 (活力女声) - 默认
- longfei_v3: 龙飞v3 (磁性男声)
- longshuo_v3: 龙硕v3 (沉稳男声)
- longyingjing_v3: 龙盈京v3 (京味女声)
- longjielidou_v3: 龙杰力豆v3 (童声)

### 如何设置音色

**方法1：直接指定音色代码**
- "语音合成 今天天气真好 使用音色 longfei_v3"
- "朗读 你好世界 用 longyue_v3"

**方法2：使用音色名称**
- "语音合成 今天天气真好 用龙飞的声音"
- "朗读 你好世界 用童声"
- "合成语音 测试文本 用京味女声"

**方法3：使用音色特征**
- "语音合成 今天天气真好 用男声"
- "朗读 你好世界 用女声"

### 支持的格式
MP3, WAV"""
