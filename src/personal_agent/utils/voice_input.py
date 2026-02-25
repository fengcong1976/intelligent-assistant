"""
语音输入模块
支持录音和语音识别功能
优先使用国内可用的语音识别服务
"""
import asyncio
import base64
import json
import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class VoiceInputManager:
    """语音输入管理器"""
    
    def __init__(self):
        self.is_recording = False
        self._recording_thread = None
        self._audio_data = []
        self._sample_rate = 16000
        self._channels = 1
        self._on_status_change: Optional[Callable] = None
        self._on_result: Optional[Callable] = None
        self._recognition_method = None
        self._init_recognition()
    
    def _init_recognition(self):
        """初始化语音识别引擎（优先国内服务）"""
        self._recognition_method = None
        
        from ..config import settings
        voice_provider = settings.llm.voice_provider or "dashscope"
        
        if voice_provider == "dashscope":
            try:
                import dashscope
                voice_api_key = settings.llm.voice_dashscope_api_key
                if voice_api_key and voice_api_key.startswith('sk-'):
                    dashscope.api_key = voice_api_key
                elif settings.llm.dashscope_api_key and settings.llm.dashscope_api_key.startswith('sk-'):
                    dashscope.api_key = settings.llm.dashscope_api_key
                else:
                    logger.warning("⚠️ DashScope API Key 无效，跳过初始化")
                    raise ValueError("Invalid API Key")
                
                from dashscope.audio.asr import Recognition, Transcription
                self._dashscope_recognition = Recognition
                self._dashscope_transcription = Transcription
                self._recognition_method = "dashscope"
                logger.info("✅ 语音识别引擎初始化成功: 阿里云 DashScope")
                return
            except ImportError:
                logger.warning("⚠️ dashscope 未安装")
            except Exception as e:
                logger.warning(f"⚠️ dashscope 初始化失败: {e}")
        
        if voice_provider == "funasr" or not self._recognition_method:
            try:
                from funasr import AutoModel
                self._funasr_model = None
                self._recognition_method = "funasr"
                logger.info("✅ 语音识别引擎初始化成功: FunASR (阿里开源离线模型)")
                return
            except ImportError:
                logger.warning("⚠️ FunASR 未安装")
        
        if voice_provider == "speech_recognition" or not self._recognition_method:
            try:
                import speech_recognition as sr
                self._sr = sr
                self._recognizer = sr.Recognizer()
                self._recognition_method = "speech_recognition"
                logger.info("✅ 语音识别引擎初始化成功: SpeechRecognition")
            except ImportError:
                logger.warning("⚠️ speech_recognition 未安装")
        
        if not self._recognition_method:
            logger.warning("❌ 没有可用的语音识别引擎")
    
    def set_callbacks(self, on_status_change: Callable = None, on_result: Callable = None):
        """设置回调函数"""
        self._on_status_change = on_status_change
        self._on_result = on_result
    
    def _notify_status(self, status: str):
        """通知状态变化"""
        if self._on_status_change:
            self._on_status_change(status)
    
    def _notify_result(self, text: str):
        """通知识别结果"""
        if self._on_result:
            cleaned_text = text.rstrip('。，！？、；：')
            self._on_result(cleaned_text)
    
    def is_available(self) -> bool:
        """检查语音识别是否可用"""
        return self._recognition_method is not None
    
    def get_install_hint(self) -> str:
        """获取安装提示"""
        return """❌ 语音识别不可用

请选择以下方式之一安装：

**方式1: 阿里云 DashScope（推荐，在线识别）**
```
pip install dashscope
```
然后在环境变量或配置文件中设置 API Key:
```
DASHSCOPE_API_KEY=your_api_key
```
获取API Key: https://dashscope.console.aliyun.com/

**方式2: FunASR（阿里开源，离线识别）**
```
pip install funasr modelscope
```
首次使用会自动下载模型（约1GB）

**方式3: SpeechRecognition（需要代理访问Google）**
```
pip install SpeechRecognition pyaudio
```"""

    def list_audio_devices(self) -> str:
        """列出所有音频设备（诊断用）"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            result = ["📋 系统音频设备列表:\n"]
            
            default_input = None
            try:
                default_info = p.get_default_input_device_info()
                default_input = default_info.get('index')
                result.append(f"🎯 默认输入设备: {default_info.get('name', '未知')}\n")
            except:
                result.append("⚠️ 未设置默认输入设备\n")
            
            result.append("\n输入设备:\n")
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info.get('maxInputChannels', 0) > 0:
                        marker = " ✓ [默认]" if i == default_input else ""
                        result.append(f"  [{i}] {info.get('name', '未知')}{marker}\n")
                        result.append(f"      采样率: {info.get('defaultSampleRate', 0)} Hz\n")
                except:
                    pass
            
            p.terminate()
            return "".join(result)
        except ImportError:
            return "❌ pyaudio 未安装: pip install pyaudio"
        except Exception as e:
            return f"❌ 获取设备列表失败: {e}"

    def start_recording(self) -> bool:
        """开始录音"""
        if self.is_recording:
            logger.warning("已经在录音中")
            return False
        
        if not self._recognition_method:
            self._notify_status("error:没有可用的语音识别引擎")
            return False
        
        try:
            import pyaudio
            
            self._audio_data = []
            self.is_recording = True
            self._notify_status("recording")
            
            def record_thread():
                p = None
                stream = None
                try:
                    p = pyaudio.PyAudio()
                    
                    devices_to_try = self._get_available_input_devices(p)
                    
                    if not devices_to_try:
                        raise OSError(-9999, "没有找到可用的输入设备")
                    
                    last_error = None
                    for device_index, device_name, sample_rate in devices_to_try:
                        try:
                            logger.info(f"🎤 尝试设备: {device_name}, 采样率: {sample_rate}")
                            
                            stream = p.open(
                                format=pyaudio.paInt16,
                                channels=self._channels,
                                rate=int(sample_rate),
                                input=True,
                                input_device_index=device_index,
                                frames_per_buffer=1024
                            )
                            
                            self._sample_rate = int(sample_rate)
                            logger.info(f"🎤 开始录音... (设备: {device_name})")
                            break
                            
                        except Exception as e:
                            last_error = e
                            logger.warning(f"设备 {device_name} 打开失败: {e}")
                            if stream:
                                try:
                                    stream.close()
                                except:
                                    pass
                            stream = None
                            continue
                    
                    if stream is None:
                        raise last_error if last_error else OSError(-9999, "所有设备都无法打开")
                    
                    while self.is_recording:
                        data = stream.read(1024, exception_on_overflow=False)
                        self._audio_data.append(data)
                    
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    
                    logger.info("🎤 录音结束")
                    
                except OSError as e:
                    error_code = getattr(e, 'errno', None)
                    error_msg = str(e)
                    logger.error(f"录音设备错误 [{error_code}]: {error_msg}")
                    
                    if stream:
                        try:
                            stream.close()
                        except:
                            pass
                    if p:
                        try:
                            p.terminate()
                        except:
                            pass
                    
                    if error_code == -9999 or "9999" in error_msg:
                        msg = f"❌ 录音设备被占用或不可用\n\n可能的原因：\n1. 其他应用正在使用麦克风\n2. 麦克风设备被禁用\n3. 立体声混音与麦克风冲突\n\n请尝试：\n• 关闭其他使用麦克风的应用（如QQ、微信、会议软件）\n• 在Windows设置中禁用立体声混音\n• 检查麦克风是否正常连接\n\n设备列表:\n{self.list_audio_devices()}"
                    elif error_code == -9996 or "Invalid" in error_msg:
                        msg = f"❌ 无效的录音设备\n\n请在Windows声音设置中检查默认录音设备\n\n{self.list_audio_devices()}"
                    elif error_code == -9997 or "Invalid sample rate" in error_msg:
                        msg = "❌ 不支持的采样率\n\n请尝试使用其他麦克风设备"
                    else:
                        msg = f"❌ 录音错误: {error_msg}"
                    
                    self.is_recording = False
                    self._notify_status(f"error:{msg}")
                    
                except Exception as e:
                    logger.error(f"录音错误: {e}")
                    
                    if stream:
                        try:
                            stream.close()
                        except:
                            pass
                    if p:
                        try:
                            p.terminate()
                        except:
                            pass
                    
                    self.is_recording = False
                    self._notify_status(f"error:录音失败: {str(e)}")
            
            import threading
            self._recording_thread = threading.Thread(target=record_thread, daemon=True)
            self._recording_thread.start()
            
            return True
            
        except ImportError:
            self._notify_status("error:需要安装 pyaudio: pip install pyaudio")
            return False
        except Exception as e:
            logger.error(f"启动录音失败: {e}")
            self._notify_status(f"error:{str(e)}")
            return False
    
    def _get_available_input_devices(self, pyaudio_instance) -> list:
        """获取可用的输入设备列表（按优先级排序）"""
        devices = []
        try:
            p = pyaudio_instance
            device_count = p.get_device_count()
            
            microphone_keywords = ['麦克风', 'microphone', 'mic', '话筒', 
                                   'usb', '蓝牙', 'bluetooth', 'headset',
                                   '耳机', '耳麦', 'webcam', '摄像头']
            
            exclude_keywords = ['立体声混音', 'stereo mix', '混音', 'mix', 
                               'virtual', '虚拟', 'loopback', '回放',
                               'output', '扬声器', 'speaker', 'hdmi', 'displayport',
                               'hd audio mic input', 'hd audio stereo']
            
            default_input_index = None
            try:
                default_input_index = p.get_default_input_device_info().get('index')
            except:
                pass
            
            for i in range(device_count):
                try:
                    info = p.get_device_info_by_index(i)
                    
                    if info.get('maxInputChannels', 0) == 0:
                        continue
                    
                    name = info.get('name', '')
                    name_lower = name.lower()
                    sample_rate = int(info.get('defaultSampleRate', 16000))
                    
                    is_excluded = any(kw in name_lower for kw in exclude_keywords)
                    
                    score = 0
                    if i == default_input_index:
                        score += 200
                    
                    if not is_excluded:
                        for kw in microphone_keywords:
                            if kw in name_lower:
                                score += 50
                        
                        if 'realtek' in name_lower and 'mic' in name_lower:
                            score += 30
                        
                        devices.append((i, name, sample_rate, score))
                    else:
                        devices.append((i, name, sample_rate, -100))
                        
                except Exception as e:
                    logger.debug(f"检查设备 {i} 失败: {e}")
                    continue
            
            devices.sort(key=lambda x: x[3], reverse=True)
            
            result = [(d[0], d[1], d[2]) for d in devices if d[3] >= 0]
            
            if not result:
                result = [(d[0], d[1], d[2]) for d in devices]
            
            logger.info(f"🎤 可用设备列表: {[(d[1], d[2]) for d in result]}")
            return result
            
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []

    def _find_microphone_device(self, pyaudio_instance) -> Optional[int]:
        """查找麦克风设备（排除立体声混音等虚拟设备）"""
        try:
            p = pyaudio_instance
            device_count = p.get_device_count()
            
            microphone_keywords = ['麦克风', 'microphone', 'mic', '话筒', '录音', 
                                   'realtek', 'usb', '蓝牙', 'bluetooth', 'headset',
                                   '耳机', '耳麦', 'webcam', '摄像头']
            
            exclude_keywords = ['立体声混音', 'stereo mix', '混音', 'mix', 
                               'virtual', '虚拟', 'loopback', '回放',
                               'output', '扬声器', 'speaker', 'hdmi', 'displayport']
            
            default_input_index = None
            best_mic_index = None
            best_mic_score = 0
            
            for i in range(device_count):
                try:
                    info = p.get_device_info_by_index(i)
                    
                    if info.get('maxInputChannels', 0) == 0:
                        continue
                    
                    name = info.get('name', '').lower()
                    
                    if p.get_default_input_device_info().get('index') == i:
                        default_input_index = i
                    
                    is_excluded = any(kw in name for kw in exclude_keywords)
                    if is_excluded:
                        logger.debug(f"跳过设备 {i}: {name} (匹配排除关键词)")
                        continue
                    
                    score = 0
                    for kw in microphone_keywords:
                        if kw in name:
                            score += 10
                    
                    if score > best_mic_score:
                        best_mic_score = score
                        best_mic_index = i
                        logger.debug(f"候选麦克风 {i}: {name} (得分: {score})")
                        
                except Exception as e:
                    logger.debug(f"检查设备 {i} 失败: {e}")
                    continue
            
            if best_mic_index is not None:
                device_info = p.get_device_info_by_index(best_mic_index)
                logger.info(f"🎤 选择麦克风设备: {device_info.get('name', '未知')}")
                return best_mic_index
            
            if default_input_index is not None:
                default_info = p.get_device_info_by_index(default_input_index)
                default_name = default_info.get('name', '').lower()
                
                if any(kw in default_name for kw in exclude_keywords):
                    logger.warning(f"⚠️ 默认输入设备可能是虚拟设备: {default_name}")
                    self._notify_status("warning:默认设备可能是立体声混音，请在系统设置中更改默认录音设备")
                
                logger.info(f"🎤 使用默认输入设备: {default_info.get('name', '未知')}")
                return default_input_index
            
            logger.warning("⚠️ 未找到合适的麦克风设备")
            return None
            
        except Exception as e:
            logger.error(f"查找麦克风设备失败: {e}")
            return None
    
    def stop_recording(self) -> str:
        """停止录音并识别"""
        if not self.is_recording:
            return ""
        
        self.is_recording = False
        self._notify_status("processing")
        
        if self._recording_thread:
            self._recording_thread.join(timeout=5)
        
        if not self._audio_data:
            self._notify_status("error:没有录到音频")
            return ""
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            self._save_wav(temp_path)
            
            result = self._recognize(temp_path)
            
            try:
                os.unlink(temp_path)
            except:
                pass
            
            if result:
                result = result.rstrip('。，！？、；：')
                self._notify_status("done")
                self._notify_result(result)
            else:
                self._notify_status("error:识别失败，请重试")
            
            return result
            
        except Exception as e:
            logger.error(f"识别失败: {e}")
            self._notify_status(f"error:{str(e)}")
            return ""
    
    def _save_wav(self, filepath: str):
        """保存为 WAV 文件"""
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self._channels)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes(b''.join(self._audio_data))
    
    def _recognize(self, audio_path: str) -> str:
        """识别音频文件"""
        if self._recognition_method == "dashscope":
            return self._recognize_with_dashscope(audio_path)
        elif self._recognition_method == "funasr":
            return self._recognize_with_funasr(audio_path)
        elif self._recognition_method == "speech_recognition":
            return self._recognize_with_sr(audio_path)
        return ""
    
    def _recognize_with_dashscope(self, audio_path: str) -> str:
        """使用阿里云 DashScope 识别"""
        try:
            from http import HTTPStatus
            import dashscope
            from ..config import settings
            
            voice_api_key = settings.llm.voice_dashscope_api_key
            if voice_api_key and voice_api_key.startswith('sk-'):
                dashscope.api_key = voice_api_key
            elif settings.llm.dashscope_api_key and settings.llm.dashscope_api_key.startswith('sk-'):
                dashscope.api_key = settings.llm.dashscope_api_key
            else:
                logger.error("DashScope API Key 无效，请检查配置")
                return ""
            
            from dashscope.audio.asr import Recognition
            
            recognition = Recognition(
                model='paraformer-realtime-v2',
                format='wav',
                sample_rate=self._sample_rate,
                language_hints=['zh', 'en'],
                callback=None
            )
            
            result = recognition.call(audio_path)
            
            if result.status_code == HTTPStatus.OK:
                sentence = result.get_sentence()
                if sentence is None:
                    logger.info("DashScope 未识别到语音内容")
                    return ""
                if isinstance(sentence, dict) and 'text' in sentence:
                    text = sentence['text'].strip()
                    logger.info(f"✅ DashScope 语音识别: {text}")
                    return text
                elif isinstance(sentence, list) and sentence:
                    ended_sentences = {}
                    seen_texts = set()
                    for item in sentence:
                        if isinstance(item, dict) and 'text' in item:
                            text = item['text'].strip()
                            sentence_id = item.get('sentence_id', 0)
                            is_end = item.get('sentence_end', False)
                            
                            normalized = text.replace(' ', '').replace('。', '').replace('，', '')
                            if is_end and text and normalized not in seen_texts:
                                seen_texts.add(normalized)
                                ended_sentences[sentence_id] = text
                    
                    if ended_sentences:
                        sorted_ids = sorted(ended_sentences.keys())
                        final_text = ''.join([ended_sentences[sid] for sid in sorted_ids])
                        logger.info(f"✅ DashScope 语音识别: {final_text}")
                        return final_text
                    
                    last_item = sentence[-1]
                    if isinstance(last_item, dict) and 'text' in last_item:
                        text = last_item['text'].strip()
                        logger.info(f"✅ DashScope 语音识别: {text}")
                        return text
                    
                    logger.info("DashScope 未识别到有效文本")
                    return ""
                else:
                    logger.warning(f"DashScope 返回格式: {type(sentence)}")
                    return ""
            else:
                logger.error(f"DashScope 识别失败: {result.message}")
                return ""
                
        except Exception as e:
            logger.error(f"DashScope 识别失败: {e}")
            return ""
    
    def _recognize_with_funasr(self, audio_path: str) -> str:
        """使用 FunASR 离线识别"""
        try:
            from funasr import AutoModel
            
            if self._funasr_model is None:
                logger.info("正在加载 FunASR 模型...")
                self._funasr_model = AutoModel(
                    model="paraformer-zh",
                    model_revision="v2.0.4",
                )
            
            result = self._funasr_model.generate(input=audio_path)
            
            if result and len(result) > 0:
                text = result[0].get("text", "")
                logger.info(f"✅ FunASR 语音识别: {text}")
                return text
            
            return ""
                
        except Exception as e:
            logger.error(f"FunASR 识别失败: {e}")
            return ""
    
    def _recognize_with_sr(self, audio_path: str) -> str:
        """使用 speech_recognition 识别（需要代理访问Google）"""
        try:
            with self._sr.AudioFile(audio_path) as source:
                audio = self._recognizer.record(source)
            
            try:
                text = self._recognizer.recognize_google(audio, language='zh-CN')
                logger.info(f"✅ Google 语音识别: {text}")
                return text
            except self._sr.UnknownValueError:
                logger.warning("无法识别音频内容")
                return ""
            except self._sr.RequestError as e:
                logger.error(f"Google 语音识别服务错误: {e}")
                return ""
                    
        except Exception as e:
            logger.error(f"speech_recognition 识别失败: {e}")
            return ""
    
    def toggle_recording(self) -> str:
        """切换录音状态"""
        if self.is_recording:
            return self.stop_recording()
        else:
            self.start_recording()
            return ""


voice_input_manager = VoiceInputManager()
