from loguru import logger
from typing import Dict, Any, Optional, List
from ..base import BaseAgent, Task
from ...tts import TTSManager
from ..email_agent import EmailAgent
import tempfile
import os
import asyncio

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
        
        try:
            from ...config import settings
            api_key = getattr(settings.llm, 'voice_dashscope_api_key', None)
            if not api_key:
                api_key = getattr(settings.llm, 'dashscope_api_key', None)
            self.tts_manager = TTSManager(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize TTSManager: {e}")
            self.tts_manager = None
    
    async def execute_task(self, task: Task) -> Any:
        if task.type == "action":
            return await self._handle_action(task.params)
        elif task.type in ("tts_speak", "synthesize_and_play"):
            return await self._synthesize_and_play(task.params)
        elif task.type == "synthesize":
            return await self._synthesize(task.params)
        elif task.type == "synthesize_and_send":
            return await self._synthesize_and_send(task.params)
        elif task.type == "list_voices":
            return self._list_voices()
        return self.cannot_handle("未知操作")
    
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
        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), f"tts_{hash(text) % 1000000}.mp3")
        
        voice = params.get("voice", "longyue_v3")
        format_type = params.get("format", "mp3")
        
        if voice not in self.AVAILABLE_VOICES:
            return self.cannot_handle(f"不支持的音色: {voice}。可用音色: {', '.join(self.AVAILABLE_VOICES.keys())}")
        
        if format_type not in ["mp3", "wav"]:
            return self.cannot_handle("格式仅支持 mp3 或 wav")
        
        try:
            result_path = await self.tts_manager.synthesize_to_file(
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
        
        output_path = os.path.join(tempfile.gettempdir(), f"tts_play_{hash(text) % 1000000}.mp3")
        
        try:
            result_path = await self.tts_manager.synthesize_to_file(
                text=text,
                output_path=output_path,
                voice=voice,
            )
            if not result_path:
                return "❌ 语音合成失败，请检查API配置"
            
            import platform
            import subprocess
            
            if platform.system() == "Windows":
                import ctypes
                winmm = ctypes.windll.winmm
                alias = "tts_play_audio"
                winmm.mciSendStringW(f'open "{result_path}" alias {alias}', None, 0, None)
                winmm.mciSendStringW(f'play {alias}', None, 0, None)
                return f"✅ 已合成并播放: {result_path}"
            else:
                for player in ["afplay", "mpg123", "ffplay"]:
                    try:
                        proc = await asyncio.create_subprocess_exec(player, result_path)
                        return f"✅ 已合成并播放: {result_path}"
                    except:
                        continue
                return f"✅ 已生成音频文件: {result_path}（未找到播放器）"
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
        
        output_path = os.path.join(tempfile.gettempdir(), f"tts_email_{hash(text) % 1000000}.mp3")
        try:
            result_path = await self.tts_manager.synthesize_to_file(
                text=text,
                output_path=output_path,
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