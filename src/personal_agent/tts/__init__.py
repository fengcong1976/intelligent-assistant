"""
阿里云语音合成 (TTS) 模块
使用 DashScope SpeechSynthesizer API 实现文本转语音
"""
import asyncio
import os
import tempfile
import threading
import time
import hashlib
from pathlib import Path
from typing import Optional, Callable, List
from loguru import logger

try:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback, AudioFormat
    DASHSCOPE_TTS_AVAILABLE = True
except ImportError:
    DASHSCOPE_TTS_AVAILABLE = False
    logger.warning("dashscope TTS 模块未安装，语音合成功能不可用")


class DashScopeTTS:
    """阿里云 DashScope 语音合成"""
    
    AVAILABLE_VOICES = {
        "longyue_v3": "龙悦v3 (活力女声)",
        "longyingjing_v3": "龙盈京v3 (京味女声)",
        "longfei_v3": "龙飞v3 (磁性男声)",
        "longshuo_v3": "龙硕v3 (沉稳男声)",
        "longjielidou_v3": "龙杰力豆v3 (童声)",
    }
    
    DEFAULT_VOICE = "longyue_v3"
    DEFAULT_MODEL = "cosyvoice-v3-flash"
    
    def __init__(self, api_key: Optional[str] = None):
        if not DASHSCOPE_TTS_AVAILABLE:
            raise ImportError("dashscope TTS 模块未安装，请运行: pip install dashscope")
        
        self.api_key = api_key
        if api_key:
            dashscope.api_key = api_key
        
        self._player_process = None
    
    def set_api_key(self, api_key: str):
        self.api_key = api_key
        dashscope.api_key = api_key
    
    def get_available_voices(self) -> dict:
        return self.AVAILABLE_VOICES
    
    async def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: str = None,
        model: str = None,
    ) -> Optional[str]:
        if not self.api_key:
            logger.error("未设置 API Key")
            return None
        
        voice = voice or self.DEFAULT_VOICE
        model = model or self.DEFAULT_MODEL
        
        if output_path is None:
            import time
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"tts_{int(time.time() * 1000)}.wav")
        
        try:
            logger.info(f"🔊 开始语音合成: {text[:50]}...")
            
            def _call_tts():
                synthesizer = SpeechSynthesizer(
                    model=model,
                    voice=voice,
                )
                return synthesizer.call(text)
            
            audio_data = await asyncio.get_event_loop().run_in_executor(None, _call_tts)
            
            if audio_data:
                output_path = output_path.replace('.wav', '.mp3')
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"✅ 语音合成完成: {output_path}")
                return output_path
            else:
                logger.error("语音合成失败: 未返回音频数据")
                return None
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"语音合成失败: {e}")
            return None
    
    async def synthesize_and_play(
        self,
        text: str,
        voice: str = None,
        model: str = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        on_complete: Optional[Callable] = None,
    ) -> bool:
        logger.info(f"🔊 synthesize_and_play 开始")
        audio_path = await self.synthesize(
            text=text,
            voice=voice,
            model=model,
        )
        
        logger.info(f"🔊 合成结果: {audio_path}")
        if audio_path and os.path.exists(audio_path):
            logger.info(f"🔊 文件存在，准备播放: {audio_path}")
            success = await self._play_audio(audio_path)
            logger.info(f"🔊 播放结果: {success}")
            try:
                os.remove(audio_path)
            except:
                pass
            
            if on_complete:
                on_complete()
            
            return success
        logger.warning(f"🔊 文件不存在或路径为空")
        return False
    
    async def _play_audio(self, audio_path: str) -> bool:
        try:
            import platform
            system = platform.system()
            logger.info(f"🔊 播放音频: {audio_path}")
            
            if system == "Windows":
                import ctypes
                from ctypes import wintypes
                
                winmm = ctypes.windll.winmm
                
                def play_mp3(path):
                    alias = "tts_audio"
                    cmd_open = f'open "{path}" alias {alias}'
                    cmd_play = f'play {alias} wait'
                    cmd_close = f'close {alias}'
                    
                    winmm.mciSendStringW(cmd_open, None, 0, None)
                    winmm.mciSendStringW(cmd_play, None, 0, None)
                    winmm.mciSendStringW(cmd_close, None, 0, None)
                
                await asyncio.get_event_loop().run_in_executor(None, play_mp3, audio_path)
                logger.info(f"🔊 播放完成")
                return True
            elif system == "Darwin":
                proc = await asyncio.create_subprocess_exec(
                    "afplay", audio_path
                )
                await proc.wait()
                return proc.returncode == 0
            else:
                for player in ["mpg123", "ffplay", "aplay", "paplay"]:
                    proc = await asyncio.create_subprocess_exec(
                        player, audio_path,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await proc.wait()
                    if proc.returncode == 0:
                        return True
                logger.error("未找到可用的音频播放器")
                return False
                
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            return False
    
    def stop_playback(self):
        if self._player_process:
            try:
                self._player_process.terminate()
                self._player_process = None
            except:
                pass


class TTSManager:
    """语音合成管理器"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "dashscope"):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.provider = provider
        self._tts = None
        self._api_key = api_key
        self._enabled = False
        self._voice = "longyue_v3"
        self._speech_rate = 1.0
        self._volume = 50
        self._stop_flag = None
        self._last_text = None
        self._is_playing = False
        self._on_stop_callback = None
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if api_key and provider == "dashscope":
            self._init_tts()
        
        self._initialized = True
    
    def set_on_stop_callback(self, callback):
        """设置停止回调"""
        self._on_stop_callback = callback
    
    def _init_tts(self):
        try:
            if DASHSCOPE_TTS_AVAILABLE:
                self._tts = DashScopeTTS(api_key=self._api_key)
                self._enabled = True
            else:
                logger.warning("语音合成模块不可用")
        except Exception as e:
            logger.error(f"初始化语音合成模块失败: {e}")
            self._enabled = False
    
    def set_api_key(self, api_key: str):
        self._api_key = api_key
        if self._tts:
            self._tts.set_api_key(api_key)
        else:
            self._init_tts()
    
    def set_voice(self, voice: str):
        v2_to_v3_mapping = {
            "longanyang": "longyue_v3",
            "longxiaochun_v2": "longyue_v3",
            "longwan_v2": "longyue_v3",
            "longyue_v2": "longyue_v3",
            "longfei_v2": "longfei_v3",
            "longjielidou_v2": "longjielidou_v3",
            "longshuo_v2": "longshuo_v3",
            "longshu_v2": "longyue_v3",
            "longhua_v2": "longyue_v3",
            "longcheng_v2": "longyue_v3",
            "longxiaoxia_v2": "longyue_v3",
            "loongbella_v2": "longyue_v3",
            "longxiaochun": "longyue_v3",
            "longwan": "longyue_v3",
            "longyue": "longyue_v3",
            "longfei": "longfei_v3",
            "longjielidou": "longjielidou_v3",
            "longshuo": "longshuo_v3",
            "longshu": "longyue_v3",
            "longhua": "longyue_v3",
            "longcheng": "longyue_v3",
            "longxiaoxia": "longyue_v3",
        }
        if voice in v2_to_v3_mapping:
            voice = v2_to_v3_mapping[voice]
        self._voice = voice
    
    def set_speech_rate(self, rate: float):
        self._speech_rate = max(0.5, min(2.0, rate))
    
    def set_volume(self, volume: int):
        self._volume = max(0, min(100, volume))
    
    def is_enabled(self) -> bool:
        return self._enabled and self._tts is not None
    
    def enable(self):
        if self._api_key:
            self._init_tts()
    
    def disable(self):
        self._enabled = False
    
    def _split_text_to_sentences(self, text: str, max_length: int = 100) -> List[str]:
        """将文本分割成句子，保持句子完整性"""
        import re
        
        sentence_endings = re.compile(r'([。！？\.\!\?]+[\s]*)')
        parts = sentence_endings.split(text)
        
        sentences = []
        current = ""
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                current += part
            else:
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        
        if current.strip():
            if sentences:
                sentences[-1] += current.strip()
            else:
                sentences.append(current.strip())
        
        merged = []
        for sentence in sentences:
            if merged and len(merged[-1]) + len(sentence) < max_length:
                merged[-1] += sentence
            else:
                merged.append(sentence)
        
        return [s for s in merged if s.strip()]
    
    def stop(self):
        """停止当前播放"""
        self._is_playing = False
        
        if self._stop_flag:
            self._stop_flag.set()
        
        stream = self._pyaudio_stream
        instance = self._pyaudio_instance
        
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if stream:
            try:
                stream.stop_stream()
                stream.close()
                logger.debug("已关闭 PyAudio 流")
            except Exception as e:
                logger.debug(f"关闭音频流失败: {e}")
        
        if instance:
            try:
                instance.terminate()
            except Exception as e:
                logger.debug(f"终止PyAudio失败: {e}")
        
        import platform
        if platform.system() == "Windows":
            try:
                import ctypes
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW('stop all', None, 0, None)
                winmm.mciSendStringW('close all', None, 0, None)
            except:
                pass
        
        if self._on_stop_callback:
            try:
                self._on_stop_callback()
            except:
                pass
    
    def stop_playback(self):
        """停止播放（兼容接口）"""
        self.stop()
    
    def _clean_text_for_tts(self, text: str) -> str:
        """清理文本中的表情符号和特殊字符，避免合成噪音"""
        import re
        
        if not text:
            return ""
        
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "\U00002702-\U000027B0"
            "]+",
            flags=re.UNICODE
        )
        
        text = emoji_pattern.sub('', text)
        
        special_chars = [
            '📍', '🔑', '📱', '🌐', '✅', '❌', '📋', '🎯', '📎', '📝', '🔊',
            '🎉', '💡', '⚠️', '❤️', '👍', '👎', '😊', '😢', '😂', '🤔',
            '👉', '👈', '👆', '👇', '✨', '🌟', '💫', '⭐', '🔥', '💪',
            '🏠', '🏢', '📧', '📞', '💬', '📢', '🔔', '⚡', '🌈', '☀️',
            '🌧️', '❄️', '🌡️', '💨', '🌊', '🌍', '🌎', '🌏', '🗺️', '🧭',
            '⏰', '⏱️', '📅', '📆', '🗓️', '🕐', '🕑', '🕒', '🕓', '🕔',
            'Ⓒ', 'Ⓡ', '™', '©', '®',
        ]
        for char in special_chars:
            text = text.replace(char, '')
        
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def speak_sync(self, text: str, voice: str = None) -> bool:
        """流式语音合成并播放（边合成边播放，降低首包延迟）"""
        import time
        import threading
        import queue
        import re
        
        if not self.is_enabled():
            return False
        
        text = self._clean_text_for_tts(text)
        if not text:
            return False
        
        old_stream = self._pyaudio_stream
        old_instance = self._pyaudio_instance
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if old_stream:
            try:
                old_stream.stop_stream()
                old_stream.close()
                logger.debug("已关闭旧的 PyAudio 流")
            except:
                pass
        
        if old_instance:
            try:
                old_instance.terminate()
            except:
                pass
        
        self._is_playing = False
        if self._stop_flag:
            self._stop_flag.set()
        
        time.sleep(0.1)
        
        self._last_text = text
        self._is_playing = True
        my_stop_flag = threading.Event()
        self._stop_flag = my_stop_flag
        
        try:
            voice = voice or self._voice
            model = self._tts.DEFAULT_MODEL if self._tts else "cosyvoice-v3-flash"
            
            logger.info(f"🔊 TTS流式合成参数: model={model}, voice={voice}")
            
            audio_queue = queue.Queue()
            first_packet_time = [None]
            start_time = time.time()
            
            class StreamCallback(ResultCallback):
                def __init__(self, q, stop_evt):
                    self.queue = q
                    self.stop_event = stop_evt
                
                def on_open(self):
                    pass
                
                def on_complete(self):
                    self.queue.put(None)
                
                def on_error(self, message: str):
                    logger.error(f"TTS流式合成错误: {message}")
                    self.queue.put(None)
                
                def on_close(self):
                    pass
                
                def on_event(self, message):
                    pass
                
                def on_data(self, data: bytes) -> None:
                    if not self.stop_event.is_set():
                        if first_packet_time[0] is None:
                            first_packet_time[0] = time.time()
                            logger.info(f"🔊 首包延迟: {(first_packet_time[0] - start_time) * 1000:.0f}ms")
                        self.queue.put(data)
            
            callback = StreamCallback(audio_queue, my_stop_flag)
            
            synthesizer = SpeechSynthesizer(
                model=model,
                voice=voice,
                format=AudioFormat.PCM_22050HZ_MONO_16BIT,
                callback=callback,
            )
            
            def synthesize_thread():
                try:
                    synthesizer.call(text)
                except Exception as e:
                    logger.error(f"合成线程错误: {e}")
                    audio_queue.put(None)
            
            synth_thread = threading.Thread(target=synthesize_thread, daemon=True)
            synth_thread.start()
            
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=22050,
                    output=True
                )
                
                self._pyaudio_instance = p
                self._pyaudio_stream = stream
                
                chunk_count = 0
                while True:
                    if my_stop_flag.is_set() or not self._is_playing:
                        break
                    try:
                        chunk = audio_queue.get(timeout=0.1)
                    except:
                        continue
                    
                    if chunk is None:
                        break
                    
                    if my_stop_flag.is_set() or not self._is_playing:
                        break
                    
                    try:
                        stream.write(chunk)
                        chunk_count += 1
                    except Exception as e:
                        logger.debug(f"写入音频流失败: {e}")
                        break
                
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
                try:
                    p.terminate()
                except:
                    pass
                
                self._pyaudio_stream = None
                self._pyaudio_instance = None
                
            except ImportError:
                logger.warning("PyAudio未安装，回退到文件播放")
                all_audio = []
                while True:
                    if my_stop_flag.is_set() or not self._is_playing:
                        break
                    try:
                        chunk = audio_queue.get(timeout=0.5)
                    except:
                        continue
                    if chunk is None:
                        break
                    all_audio.append(chunk)
                
                if all_audio and not my_stop_flag.is_set() and self._is_playing:
                    import wave
                    temp_dir = tempfile.gettempdir()
                    audio_path = os.path.join(temp_dir, f"tts_{int(time.time() * 1000)}.wav")
                    
                    with wave.open(audio_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(22050)
                        wf.writeframes(b''.join(all_audio))
                    
                    import platform
                    if platform.system() == "Windows":
                        import ctypes
                        winmm = ctypes.windll.winmm
                        alias = "tts_audio"
                        winmm.mciSendStringW(f'open "{audio_path}" alias {alias}', None, 0, None)
                        winmm.mciSendStringW(f'play {alias}', None, 0, None)
                        
                        while True:
                            if my_stop_flag.is_set() or not self._is_playing:
                                winmm.mciSendStringW(f'stop {alias}', None, 0, None)
                                winmm.mciSendStringW(f'close {alias}', None, 0, None)
                                break
                            
                            status = ctypes.create_unicode_buffer(128)
                            winmm.mciSendStringW(f'status {alias} mode', status, 128, None)
                            if 'stopped' in status.value.lower() or 'not ready' in status.value.lower():
                                winmm.mciSendStringW(f'close {alias}', None, 0, None)
                                break
                            
                            time.sleep(0.05)
                    
                    try:
                        os.remove(audio_path)
                    except:
                        pass
            
            synth_thread.join(timeout=2)
            self._is_playing = False
            return True
            
        except Exception as e:
            logger.error(f"流式语音播放失败: {e}")
            self._is_playing = False
            return False
    
    def speak_sync_with_cache(self, text: str, voice: str = None) -> Optional[str]:
        """同步语音合成并返回音频文件路径（用于缓存）"""
        import time
        import hashlib
        
        if not self.is_enabled():
            return None
        
        text = self._clean_text_for_tts(text)
        if not text:
            return None
        
        old_stream = self._pyaudio_stream
        old_instance = self._pyaudio_instance
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if old_stream:
            try:
                old_stream.stop_stream()
                old_stream.close()
            except:
                pass
        
        if old_instance:
            try:
                old_instance.terminate()
            except:
                pass
        
        self._is_playing = False
        if self._stop_flag:
            self._stop_flag.set()
        
        time.sleep(0.1)
        
        my_stop_flag = threading.Event()
        self._stop_flag = my_stop_flag
        self._last_text = text
        self._is_playing = True
        
        try:
            voice = voice or self._voice
            model = self._tts.DEFAULT_MODEL if self._tts else "cosyvoice-v3-flash"
            
            text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"tts_cache_{text_hash}.mp3")
            
            if os.path.exists(audio_path):
                self._play_cached_file(audio_path)
                return audio_path
            
            try:
                synthesizer = SpeechSynthesizer(model=model, voice=voice)
                audio_data = synthesizer.call(text)
                
                if audio_data:
                    with open(audio_path, 'wb') as f:
                        f.write(audio_data)
                    
                    self._play_cached_file(audio_path)
                    return audio_path
                
                return None
                
            except Exception as e:
                logger.error(f"合成失败: {e}")
                return None
            
        except Exception as e:
            logger.error(f"语音合成缓存失败: {e}")
            self._is_playing = False
            return None
    
    def _play_cached_file(self, audio_path: str) -> bool:
        """播放缓存的音频文件"""
        import platform
        
        try:
            if platform.system() == "Windows":
                import ctypes
                winmm = ctypes.windll.winmm
                alias = "tts_cached_audio"
                winmm.mciSendStringW(f'open "{audio_path}" alias {alias}', None, 0, None)
                winmm.mciSendStringW(f'play {alias}', None, 0, None)
                
                while True:
                    if self._stop_flag and self._stop_flag.is_set():
                        winmm.mciSendStringW(f'stop {alias}', None, 0, None)
                        winmm.mciSendStringW(f'close {alias}', None, 0, None)
                        break
                    
                    if not self._is_playing:
                        winmm.mciSendStringW(f'stop {alias}', None, 0, None)
                        winmm.mciSendStringW(f'close {alias}', None, 0, None)
                        break
                    
                    status = ctypes.create_unicode_buffer(128)
                    winmm.mciSendStringW(f'status {alias} mode', status, 128, None)
                    if 'stopped' in status.value.lower() or 'not ready' in status.value.lower():
                        winmm.mciSendStringW(f'close {alias}', None, 0, None)
                        break
                    
                    time.sleep(0.05)
            else:
                import subprocess
                process = subprocess.Popen(['afplay', audio_path])
                while process.poll() is None:
                    if self._stop_flag and self._stop_flag.is_set():
                        process.terminate()
                        break
                    if not self._is_playing:
                        process.terminate()
                        break
                    time.sleep(0.05)
            
            self._is_playing = False
            return True
            
        except Exception as e:
            logger.error(f"播放缓存音频失败: {e}")
            self._is_playing = False
            return False
    
    def play_cached(self, audio_path: str) -> bool:
        """播放缓存的音频文件"""
        if not os.path.exists(audio_path):
            return False
        
        old_stream = self._pyaudio_stream
        old_instance = self._pyaudio_instance
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if old_stream:
            try:
                old_stream.stop_stream()
                old_stream.close()
            except:
                pass
        
        if old_instance:
            try:
                old_instance.terminate()
            except:
                pass
        
        self._is_playing = False
        if self._stop_flag:
            self._stop_flag.set()
        
        time.sleep(0.1)
        
        self._is_playing = True
        self._stop_flag = threading.Event()
        
        return self._play_cached_file(audio_path)
    
    def get_last_text(self) -> Optional[str]:
        return self._last_text
    
    def replay_last(self) -> bool:
        if self._last_text:
            return self.speak_sync(self._last_text)
        return False

    async def speak(self, text: str, voice: str = None) -> bool:
        if not self.is_enabled():
            logger.warning("语音合成未启用")
            return False
        
        text = text.strip()
        if not text:
            return False
        
        if len(text) > 500:
            text = text[:500] + "..."
        
        logger.info(f"🔊 TTSManager.speak 开始: {text[:50]}...")
        result = await self._tts.synthesize_and_play(
            text=text,
            voice=voice or self._voice,
            speech_rate=self._speech_rate,
            volume=self._volume,
        )
        logger.info(f"🔊 TTSManager.speak 结果: {result}")
        return result
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: str = None
    ) -> Optional[str]:
        if not self.is_enabled():
            return None
        
        return await self._tts.synthesize(
            text=text,
            output_path=output_path,
            voice=voice or self._voice,
        )
    
    def get_available_voices(self) -> dict:
        if self._tts:
            return self._tts.get_available_voices()
        return {}
    
    def stop(self):
        """停止播放"""
        self._is_playing = False
        
        if self._stop_flag:
            self._stop_flag.set()
        
        stream = self._pyaudio_stream
        instance = self._pyaudio_instance
        
        self._pyaudio_stream = None
        self._pyaudio_instance = None
        
        if stream:
            try:
                stream.stop_stream()
                stream.close()
                logger.debug("已关闭 PyAudio 流")
            except Exception as e:
                logger.debug(f"关闭音频流失败: {e}")
        
        if instance:
            try:
                instance.terminate()
            except Exception as e:
                logger.debug(f"终止PyAudio失败: {e}")
        
        import platform
        if platform.system() == "Windows":
            try:
                import ctypes
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW('stop all', None, 0, None)
                winmm.mciSendStringW('close all', None, 0, None)
            except:
                pass
        
        if self._tts:
            try:
                self._tts.stop_playback()
            except:
                pass
        
        if self._on_stop_callback:
            try:
                self._on_stop_callback()
            except:
                pass


_tts_manager: Optional[TTSManager] = None


def get_tts_manager() -> TTSManager:
    global _tts_manager
    if _tts_manager is None:
        from ..config import Settings
        settings = Settings()
        api_key = settings.llm.voice_dashscope_api_key or settings.llm.dashscope_api_key
        provider = settings.llm.voice_provider
        _tts_manager = TTSManager(api_key=api_key, provider=provider)
        if settings.llm.tts_enabled:
            _tts_manager.enable()
        else:
            _tts_manager.disable()
        _tts_manager.set_voice(settings.llm.tts_voice)
        _tts_manager.set_speech_rate(settings.llm.tts_speech_rate)
    return _tts_manager


def init_tts(api_key: str = None, provider: str = "dashscope") -> TTSManager:
    global _tts_manager
    if api_key is None:
        from ..config import Settings
        settings = Settings()
        settings.reload()  # 重新加载配置以获取最新设置
        api_key = settings.llm.voice_dashscope_api_key or settings.llm.dashscope_api_key
        provider = settings.llm.voice_provider
        _tts_manager = TTSManager(api_key=api_key, provider=provider)
        if settings.llm.tts_enabled:
            _tts_manager.enable()
        else:
            _tts_manager.disable()
        _tts_manager.set_voice(settings.llm.tts_voice)
        _tts_manager.set_speech_rate(settings.llm.tts_speech_rate)
    else:
        _tts_manager = TTSManager(api_key=api_key, provider=provider)
    return _tts_manager
