"""
独立的语音合成播放器 - 专门给语音合成智能体使用
与系统消息的发声完全分开
"""
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer
    DASHSCOPE_TTS_AVAILABLE = True
except ImportError:
    DASHSCOPE_TTS_AVAILABLE = False
    logger.warning("dashscope TTS 模块未安装，语音合成功能不可用")


class TTSPlayer:
    """独立的语音合成播放器"""
    
    DEFAULT_VOICE = "longyue_v3"
    DEFAULT_MODEL = "cosyvoice-v3-flash"
    
    def __init__(self, api_key: str = None):
        """
        初始化 TTS 播放器
        
        Args:
            api_key: 语音合成 API Key，如果不提供则尝试从配置读取
        """
        self._api_key = api_key
        self._voice = self.DEFAULT_VOICE
        self._speech_rate = 1.0
        
        if not self._api_key:
            self._load_api_key_from_config()
        
        if self._api_key:
            dashscope.api_key = self._api_key
    
    def _load_api_key_from_config(self):
        """从配置加载 API Key"""
        try:
            from ...config import settings
            self._api_key = getattr(settings.llm, 'voice_dashscope_api_key', None)
            if not self._api_key:
                self._api_key = getattr(settings.llm, 'dashscope_api_key', None)
        except Exception as e:
            logger.error(f"Failed to load API key from config: {e}")
            self._api_key = None
    
    def set_voice(self, voice: str):
        """设置音色"""
        self._voice = voice
    
    def set_speech_rate(self, rate: float):
        """设置语速"""
        self._speech_rate = max(0.5, min(2.0, rate))
    
    async def synthesize_to_file(self, text: str, output_path: str = None, voice: str = None) -> Optional[str]:
        """
        将文本合成为音频文件
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径，如果不提供则使用临时文件
            voice: 音色，如果不提供则使用默认音色
            
        Returns:
            输出文件路径，失败则返回 None
        """
        if not DASHSCOPE_TTS_AVAILABLE:
            logger.error("TTSPlayer: dashscope TTS 模块未安装")
            return None
        
        if not self._api_key:
            logger.error("TTSPlayer: API key not available")
            return None
        
        if not text:
            logger.error("TTSPlayer: Empty text")
            return None
        
        if not output_path:
            import uuid
            import time
            output_path = os.path.join(tempfile.gettempdir(), f"tts_player_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.mp3")
        
        voice = voice or self._voice
        
        try:
            logger.info(f"TTSPlayer: 开始语音合成: {text[:50]}...")
            
            def _call_tts():
                synthesizer = SpeechSynthesizer(
                    model=self.DEFAULT_MODEL,
                    voice=voice,
                )
                return synthesizer.call(text)
            
            audio_data = await asyncio.get_event_loop().run_in_executor(None, _call_tts)
            
            if audio_data:
                output_path = output_path.replace('.wav', '.mp3')
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"TTSPlayer: 语音合成完成: {output_path}")
                return output_path
            else:
                logger.error("TTSPlayer: 语音合成失败: 未返回音频数据")
                return None
                
        except Exception as e:
            logger.exception(f"TTSPlayer: Synthesis failed: {e}")
            return None
    
    async def speak(self, text: str, voice: str = None) -> bool:
        """
        合成并播放语音
        
        Args:
            text: 要播放的文本
            voice: 音色
            
        Returns:
            是否成功
        """
        output_path = await self.synthesize_to_file(text, voice=voice)
        if not output_path:
            return False
        
        return await self._play_audio(output_path)
    
    async def _play_audio(self, file_path: str) -> bool:
        """播放音频文件"""
        import platform
        
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows 使用 Windows Media Player API
                import ctypes
                winmm = ctypes.windll.winmm
                alias = f"tts_player_{hash(file_path) % 10000}"
                
                # 打开音频文件
                result = winmm.mciSendStringW(f'open "{file_path}" alias {alias}', None, 0, None)
                if result != 0:
                    logger.error(f"TTSPlayer: Failed to open audio file, error code: {result}")
                    return False
                
                # 播放音频
                result = winmm.mciSendStringW(f'play {alias}', None, 0, None)
                if result != 0:
                    logger.error(f"TTSPlayer: Failed to play audio, error code: {result}")
                    return False
                
                logger.info(f"TTSPlayer: Playing audio {file_path}")
                return True
                
            elif system == "Darwin":  # macOS
                proc = await asyncio.create_subprocess_exec("afplay", file_path)
                await proc.wait()
                return proc.returncode == 0
                
            elif system == "Linux":
                # 尝试不同的播放器
                for player in ["mpg123", "ffplay", "aplay"]:
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            player, file_path,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await proc.wait()
                        if proc.returncode == 0:
                            return True
                    except:
                        continue
                
                logger.error("TTSPlayer: No suitable audio player found")
                return False
                
            else:
                logger.error(f"TTSPlayer: Unsupported platform: {system}")
                return False
                
        except Exception as e:
            logger.exception(f"TTSPlayer: Play audio failed: {e}")
            return False
