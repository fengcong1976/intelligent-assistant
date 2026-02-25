"""
Music Agent - 专业音乐播放智能体
支持播放控制、播放列表管理、音乐库搜索
"""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from ..base import BaseAgent, Task, Message
from ...config import settings
from ...music import MusicPlayer, Song, PlayMode

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from skills.music_player.simple_player import execute as music_execute
except ImportError as e:
    logger.error(f"❌ 音乐播放器加载失败: {e}")
    async def music_execute(*args, **kwargs):
        return "❌ 音乐播放器未加载"


class MusicAgent(BaseAgent):
    """专业音乐播放智能体"""
    
    PRIORITY = 3
    KEYWORD_MAPPINGS = {
        "播放": ("play", {}),
        "播放音乐": ("play", {}),
        "放音乐": ("play", {}),
        "暂停": ("pause", {}),
        "暂停音乐": ("pause", {}),
        "暂停播放": ("pause", {}),
        "停止": ("stop", {}),
        "停止音乐": ("stop", {}),
        "停止播放": ("stop", {}),
        "继续": ("resume", {}),
        "继续播放": ("resume", {}),
        "继续音乐": ("resume", {}),
        "下一首": ("next", {}),
        "下一曲": ("next", {}),
        "上一首": ("previous", {}),
        "上一曲": ("previous", {}),
        "切歌": ("next", {}),
        "换歌": ("next", {}),
        "静音": ("volume_mute", {}),
        "取消静音": ("volume_unmute", {}),
        "声音大一点": ("volume_up", {}),
        "声音小一点": ("volume_down", {}),
        "大声点": ("volume_up", {}),
        "小声点": ("volume_down", {}),
        "音量大一点": ("volume_up", {}),
        "音量小一点": ("volume_down", {}),
        "音量调高点": ("volume_up", {}),
        "音量调低点": ("volume_down", {}),
        "调大音量": ("volume_up", {}),
        "调小音量": ("volume_down", {}),
        "增加音量": ("volume_up", {}),
        "降低音量": ("volume_down", {}),
        "音量加": ("volume_up", {}),
        "音量减": ("volume_down", {}),
        "打开音乐播放器": ("open_player", {}),
        "音乐播放器": ("open_player", {}),
        "打开播放器": ("open_player", {}),
        "显示播放器": ("open_player", {}),
        "扫描音乐": ("scan_library", {}),
        "扫描音乐库": ("scan_library", {}),
        "重新扫描": ("scan_library", {}),
        "刷新音乐库": ("scan_library", {}),
        "更新音乐库": ("scan_library", {}),
    }

    def __init__(self):
        super().__init__(
            name="music_agent",
            description="专业音乐播放智能体 - 完整的音乐播放和管理"
        )

        self.register_capability(
            capability="play_music",
            description="播放音乐。当用户要求播放歌曲、歌手的音乐时必须调用此工具。可以播放指定歌曲、歌手的音乐，或随机播放。",
            aliases=[
                "播放音乐", "播放歌曲", "放首歌", "放歌", "听歌", "听音乐", "来首歌", "来点音乐", "放点音乐",
                "暂停音乐", "暂停歌曲", "停歌", "暂停播放音乐", "暂停播放歌曲",
                "停止音乐", "停止歌曲", "停掉音乐", "停掉歌曲", "停止播放音乐",
                "继续音乐", "继续歌曲", "继续播放音乐", "继续播放歌曲",
                "下一首", "下一曲", "切歌", "换歌", "跳过", "下一首歌", "下一曲歌",
                "上一首", "上一曲", "上一首歌", "上一曲歌"
            ],
            alias_params={
                "暂停音乐": {"action": "pause"},
                "暂停歌曲": {"action": "pause"},
                "停歌": {"action": "pause"},
                "暂停播放音乐": {"action": "pause"},
                "暂停播放歌曲": {"action": "pause"},
                "停止音乐": {"action": "stop"},
                "停止歌曲": {"action": "stop"},
                "停掉音乐": {"action": "stop"},
                "停掉歌曲": {"action": "stop"},
                "停止播放音乐": {"action": "stop"},
                "继续音乐": {"action": "play"},
                "继续歌曲": {"action": "play"},
                "继续播放音乐": {"action": "play"},
                "继续播放歌曲": {"action": "play"},
                "下一首": {"action": "next"},
                "下一曲": {"action": "next"},
                "切歌": {"action": "next"},
                "换歌": {"action": "next"},
                "跳过": {"action": "next"},
                "下一首歌": {"action": "next"},
                "下一曲歌": {"action": "next"},
                "上一首": {"action": "previous"},
                "上一曲": {"action": "previous"},
                "上一首歌": {"action": "previous"},
                "上一曲歌": {"action": "previous"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "song": {
                        "type": "string",
                        "description": "歌曲名称（可选）"
                    },
                    "artist": {
                        "type": "string",
                        "description": "歌手名称（可选）"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "stop", "next", "previous"],
                        "description": "播放控制动作",
                        "default": "play"
                    }
                },
                "required": []
            },
            category="music"
        )
        
        self.register_capability(
            capability="scan_music_library",
            description="扫描音乐库，重新加载所有音乐文件。当用户要求扫描音乐、刷新音乐库、更新音乐库时必须调用此工具。",
            aliases=[
                "扫描音乐", "扫描音乐库", "重新扫描", "刷新音乐库", "更新音乐库", "扫描歌曲", "刷新歌曲", "更新歌曲"
            ],
            alias_params={},
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            category="music"
        )
        
        self.register_capability("play_audio", "播放音频")
        self.register_capability("stop_audio", "停止音频")
        self.register_capability("control_playback", "播放控制")
        self.register_capability("search_local_music", "搜索本地音乐")
        self.register_capability("playlist_management", "播放列表管理")
        self.register_capability("volume_control", "音量控制")
        
        # 注册支持的文件格式（类似Windows文件关联）
        self.register_file_formats(
            open_formats=[".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac", ".ncm"]
        )

        self.player: Optional[MusicPlayer] = None
        self.supported_formats = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".ncm"]
        
        self._init_player()

    def _init_player(self):
        """初始化播放器"""
        music_library = self._get_music_library()
        self.player = MusicPlayer(music_library=music_library)
        self.player.set_on_song_change_callback(self._on_song_changed)

    def _on_song_changed(self, song):
        """歌曲切换回调"""
        if song:
            self._show_music_minimized_item()
            self._notify_song_change(song)

    def _notify_song_change(self, song):
        """通知对话框歌曲切换"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat_window'):
                        main_window = widget
                        if hasattr(main_window, 'chat_window'):
                            chat_window = main_window.chat_window
                            if hasattr(chat_window, 'signal_helper'):
                                song_info = f"🎵 正在播放: {song.title}"
                                if song.artist:
                                    song_info = f"🎵 正在播放: {song.artist} - {song.title}"
                                chat_window.signal_helper.emit_append_message("assistant", song_info)
                                break
        except Exception as e:
            logger.warning(f"通知歌曲切换失败: {e}")

    def _send_message_to_chat(self, message: str):
        """发送即时消息到对话框"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat_window'):
                        main_window = widget
                        if hasattr(main_window, 'chat_window'):
                            chat_window = main_window.chat_window
                            if hasattr(chat_window, 'signal_helper'):
                                chat_window.signal_helper.emit_append_message("assistant", message)
                                break
        except Exception as e:
            logger.warning(f"发送消息失败: {e}")

    def _get_player(self) -> MusicPlayer:
        if self.player is None:
            self._init_player()
        return self.player

    def _get_music_library(self) -> Path:
        return settings.directory.get_music_library()

    def _show_music_minimized_item(self):
        """显示音乐播放器最小化条目"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat_window'):
                        main_window = widget
                        if hasattr(main_window, 'chat_window'):
                            chat_window = main_window.chat_window
                            if hasattr(chat_window, 'signal_helper'):
                                chat_window.signal_helper.emit_show_music_minimized()
                                break
        except Exception as e:
            logger.warning(f"显示音乐播放器最小化条目失败: {e}")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params
        if task_type in ("play", "play_music"):
            result = await self._handle_play(params)
            if result and ("未找到歌曲" in result or "未找到歌手" in result):
                task.no_retry = True
            return result
        elif task_type == "general":
            text = params.get("text", params.get("original_text", "")).lower()
            return await self._handle_general(text, params)
        elif task_type == "stop":
            return await self._handle_stop(params)
        elif task_type == "pause":
            return await self._handle_pause(params)
        elif task_type == "resume":
            return await self._handle_resume(params)
        elif task_type == "next":
            return await self._handle_next(params)
        elif task_type == "previous":
            return await self._handle_previous(params)
        elif task_type == "volume":
            return await self._handle_volume(params)
        elif task_type == "volume_mute":
            return await self._handle_volume_mute(params)
        elif task_type == "volume_unmute":
            return await self._handle_volume_unmute(params)
        elif task_type == "volume_up":
            return await self._handle_volume_up(params)
        elif task_type == "volume_down":
            return await self._handle_volume_down(params)
        elif task_type == "mode":
            return await self._handle_mode(params)
        elif task_type == "status":
            return await self._handle_status(params)
        elif task_type == "search":
            return await self._handle_search(params)
        elif task_type == "list":
            return await self._handle_list(params)
        elif task_type == "playlist":
            return await self._handle_playlist(params)
        elif task_type == "favorite":
            return await self._handle_favorite(params)
        elif task_type == "history":
            return await self._handle_history(params)
        elif task_type == "get_current_playing_file":
            return await self._handle_get_current_file(params)
        elif task_type == "get_curreent_playing_file":
            return await self._handle_get_current_file(params)
        elif task_type == "open_player":
            return await self._handle_open_player(params)
        elif task_type in ("scan_library", "scan_music_library"):
            return await self._handle_scan_library(params)
        else:
            return f"❌ 不支持的音乐操作: {task_type}"
    
    async def _handle_general(self, text: str, params: Dict) -> str:
        """处理 general 类型任务，增强意图识别"""
        text_lower = text.lower()
        
        stop_keywords = ["停止", "停", "关掉", "关闭", "不要放", "别放"]
        if any(kw in text_lower for kw in stop_keywords):
            return await self._handle_stop(params)
        
        pause_keywords = ["暂停", "pause", "等一下", "先停"]
        if any(kw in text_lower for kw in pause_keywords):
            return await self._handle_pause(params)
        
        resume_keywords = ["继续", "恢复", "resume", "接着放", "继续放"]
        if any(kw in text_lower for kw in resume_keywords):
            return await self._handle_resume(params)
        
        next_keywords = ["下一首", "下一曲", "next", "换个", "换一首", "跳过"]
        if any(kw in text_lower for kw in next_keywords):
            return await self._handle_next(params)
        
        prev_keywords = ["上一首", "上一曲", "previous", "上一首", "前一首"]
        if any(kw in text_lower for kw in prev_keywords):
            return await self._handle_previous(params)
        
        play_keywords = ["播放", "放", "听", "来首", "来一曲", "唱", "放首", "放一首"]
        if any(kw in text_lower for kw in play_keywords):
            return await self._handle_play(params)
        
        if "音乐" in text_lower or "歌" in text_lower:
            return await self._handle_play(params)
        
        return f"❌ 无法识别的音乐指令: {text}"

    async def _handle_search(self, params: Dict) -> str:
        query = params.get("query", params.get("original_text", "")).lower()
        if not query:
            return "❌ 请提供搜索关键词"
        
        original_text = params.get("original_text", "")
        query = query.replace(".mp3", "").replace(".MP3", "").strip()
        query = query.replace("我们有", "").replace("这首歌吗", "").replace("吗", "").strip()
        
        auto_play = False
        play_keywords = ["播放", "放", "听", "如果有", "请播放", "来首", "来一曲"]
        for keyword in play_keywords:
            if keyword in original_text:
                auto_play = True
                query = query.replace(keyword, "").replace("？", "").strip()
                break
        
        player = self._get_player()
        songs = player.get_cached_songs()
        
        logger.debug(f"🎵 缓存歌曲数量: {len(songs) if songs else 0}")
        if songs:
            logger.debug(f"🎵 第一首歌曲类型: {type(songs[0])}")
        
        if not songs:
            songs = player.scan_music_library()
        
        results = []
        for s in songs:
            if isinstance(s, str):
                logger.warning(f"⚠️ 歌曲是字符串: {s}")
                continue
            title_lower = s.title.lower()
            path_lower = s.path.lower()
            if query in title_lower or query in path_lower:
                results.append(s)
        
        if not results:
            return f"❌ 未找到包含 '{query}' 的歌曲"
        
        if auto_play and results:
            song = results[0]
            logger.debug(f"🎵 自动播放歌曲类型: {type(song)}, 内容: {song}")
            if isinstance(song, str):
                return f"❌ 歌曲数据格式错误: {song}"
            player.play(song=song)
            self._show_music_minimized_item()
            return f"🔍 找到 {len(results)} 首相关歌曲\n\n🎵 正在播放: {song.title if hasattr(song, 'title') else str(song)}"
        
        response = f"🔍 找到 {len(results)} 首相关歌曲:\n\n"
        for i, song in enumerate(results[:10], 1):
            title = song.title if hasattr(song, 'title') else str(song)
            response += f"{i}. {title}\n"
        
        return response

    async def _handle_list(self, params: Dict) -> str:
        player = self._get_player()
        songs = player.scan_music_library()
        
        if not songs:
            return "❌ 音乐库中没有找到音乐文件"
        
        response = f"🎵 音乐库 (共 {len(songs)} 首):\n\n"
        for i, song in enumerate(songs[:20], 1):
            response += f"{i}. {song.title}\n"
        
        if len(songs) > 20:
            response += f"\n... 还有 {len(songs) - 20} 首"
        
        return response

    async def _handle_play(self, params: Dict) -> str:
        source = params.get("source", "")
        title = params.get("title", "")
        song_name = params.get("song_name", "") or params.get("song", "")
        artist = params.get("artist", "")
        file_path = params.get("file_path", "")
        action = params.get("action", "play")
        
        original_text = params.get("original_text", "")
        logger.info(f"🎵 _handle_play 参数: source={source}, title={title}, song_name={song_name}, artist={artist}, file_path={file_path}, action={action}")
        logger.info(f"🎵 original_text: {original_text}")
        
        if action == "next":
            return await self._handle_next(params)
        elif action == "previous":
            return await self._handle_previous(params)
        elif action == "pause":
            return await self._handle_pause(params)
        elif action == "stop":
            return await self._handle_stop(params)
        
        if not song_name and not artist:
            if original_text:
                import re
                match = re.search(r'播放(.+?)的(.+?)(?:的歌)?$', original_text)
                if match:
                    artist = match.group(1).strip()
                    song_name = match.group(2).strip()
                    if song_name in ["歌", "歌曲", "的歌"]:
                        song_name = ""
                else:
                    match = re.search(r'播放(.+?)(?:的歌)?$', original_text)
                    if match:
                        potential = match.group(1).strip()
                        if "的" in potential:
                            parts = potential.split("的")
                            artist = parts[0].strip()
                            song_name = parts[1].strip() if len(parts) > 1 else ""
                        else:
                            song_name = potential

        player = self._get_player()
        logger.info(f"🎵 player 状态: is_playing={player.is_playing}, current_song={player.current_song.title if player.current_song else None}")
        logger.info(f"🎵 last_song_path={player.last_song_path}")
        
        if file_path:
            path = Path(file_path)
            if path.exists():
                song = Song(path=str(path), title=title or path.stem)
                player.play(song=song)
                self._show_music_minimized_item()
                return f"▶️ 正在播放: {song.title}"
            else:
                return f"❌ 文件不存在: {file_path}"
        
        songs = player.get_cached_songs()
        if not songs:
            songs = player.scan_music_library()
        
        logger.info(f"🎵 歌曲数量: {len(songs) if songs else 0}")
        
        generic_patterns = ['播放音乐', '播放歌', '放音乐', '放歌', '听音乐', '听歌', '来首音乐', '来首歌', '音乐', '歌', '歌曲']
        is_generic_request = False
        if original_text:
            text_lower = original_text.strip().lower()
            for pattern in generic_patterns:
                if text_lower == pattern or text_lower == f"播放{pattern}":
                    is_generic_request = True
                    break
        
        if is_generic_request and not artist and not song_name:
            logger.info(f"🎵 检测到通用播放请求，跳过歌曲搜索")
            song_name = None
            artist = None
        
        if artist or song_name:
            logger.info(f"🎵 搜索歌曲: artist={artist}, song_name={song_name}")
            try:
                matches = []
                for s in songs:
                    is_match = False
                    match_score = 0
                    song_title = s.title.lower()
                    song_artist = (s.artist or "").lower()
                    song_path = str(s.path).lower() if hasattr(s, 'path') and s.path else ""
                    
                    full_text = f"{song_artist} {song_title}".lower()
                    
                    if artist and song_name:
                        artist_in_song = artist.lower() in song_title or artist.lower() in song_artist
                        songname_in_song = song_name.lower() in song_title or song_name.lower() in song_path
                        if artist_in_song and songname_in_song:
                            is_match = True
                            match_score = 3
                    elif artist:
                        if artist.lower() in song_title or artist.lower() in song_artist:
                            is_match = True
                            match_score = 2
                    elif song_name:
                        song_name_lower = song_name.lower()
                        if song_name_lower in song_title:
                            is_match = True
                            match_score = 3
                        elif song_name_lower in song_artist:
                            is_match = True
                            match_score = 2
                        elif song_name_lower in song_path:
                            is_match = True
                            match_score = 1
                        elif song_title in song_name_lower or song_name_lower in song_title.replace(" ", ""):
                            is_match = True
                            match_score = 1
                    
                    if is_match:
                        matches.append((s, match_score))
                
                logger.info(f"🎵 搜索完成: matches={len(matches)}")
                if matches:
                    matches.sort(key=lambda x: x[1], reverse=True)
                    song = matches[0][0]
                    logger.info(f"🎵 找到匹配歌曲: {song.title} (score={matches[0][1]})")
                    player.play(song=song)
                    self._show_music_minimized_item()
                    if artist and song_name:
                        return f"▶️ 正在播放: {song.artist} - {song.title}" if song.artist else f"▶️ 正在播放: {song.title}"
                    elif artist:
                        return f"▶️ 正在播放歌手 {artist} 的歌曲: {song.title}"
                    else:
                        return f"▶️ 正在播放: {song.title}"
                
                logger.info(f"🎵 未找到匹配歌曲，返回错误消息")
                if artist and not song_name:
                    return f"❌ 未找到歌手 {artist} 的歌曲"
                elif song_name and not artist:
                    return f"❌ 未找到歌曲: {song_name}"
                else:
                    return f"❌ 未找到 {artist} 的歌曲 {song_name}"
            except Exception as e:
                logger.error(f"🎵 搜索歌曲时发生异常: {e}")
                logger.exception("🎵 搜索异常详情:")
                return f"❌ 搜索歌曲时发生错误: {e}"
        
        logger.info(f"🎵 跳过搜索，继续执行其他逻辑")
        
        if source:
            song = Song(path=source, title=title or Path(source).stem)
            player.play(song=song)
            self._show_music_minimized_item()
            return f"▶️ 正在播放: {song.title}"
        
        logger.info(f"🎵 检查播放状态: is_playing={player.is_playing}")
        if player.is_playing:
            logger.info(f"🎵 已在播放中: {player.current_song.title if player.current_song else '未知'}")
            return f"🎵 正在播放: {player.current_song.title if player.current_song else '未知'}"
        
        logger.info(f"🎵 检查 current_song: {player.current_song.title if player.current_song else None}")
        if player.current_song:
            logger.info(f"🎵 调用 resume()")
            player.resume()
            self._show_music_minimized_item()
            return f"▶️ 继续播放: {player.current_song.title}"
        
        logger.info(f"🎵 获取 last_played_song")
        last_song = player.get_last_played_song()
        logger.info(f"🎵 last_song: {last_song.title if last_song else None}")
        if last_song:
            logger.info(f"🎵 播放 last_song: {last_song.title}")
            player.play(song=last_song)
            self._show_music_minimized_item()
            return f"▶️ 继续播放: {last_song.title}"
        
        logger.info(f"🎵 播放第一首歌")
        if songs:
            song = songs[0]
            player.play(song=song)
            self._show_music_minimized_item()
            return f"▶️ 正在播放: {song.title}"
        
        return "❌ 音乐库中没有歌曲，请先扫描音乐库"

    async def _handle_stop(self, params: Dict) -> str:
        player = self._get_player()
        player.stop()
        return "⏹️ 播放已停止"

    async def _handle_pause(self, params: Dict) -> str:
        player = self._get_player()
        player.pause()
        return "⏸️ 播放已暂停"

    async def _handle_resume(self, params: Dict) -> str:
        player = self._get_player()
        player.resume()
        return "▶️ 继续播放"

    async def _handle_next(self, params: Dict) -> str:
        player = self._get_player()
        if player.next_song():
            return f"⏭️ 下一首: {player.current_song.title}"
        return "❌ 没有下一首歌曲"

    async def _handle_previous(self, params: Dict) -> str:
        player = self._get_player()
        if player.previous_song():
            return f"⏮️ 上一首: {player.current_song.title}"
        return "❌ 没有上一首歌曲"

    async def _handle_volume(self, params: Dict) -> str:
        player = self._get_player()
        action = params.get("action", "")
        
        if action == "up":
            player.volume_up()
        elif action == "down":
            player.volume_down()
        elif action == "set":
            volume = params.get("value", 0.5)
            player.set_volume(volume)
        else:
            volume = params.get("value", 0.7)
            player.set_volume(volume)
        
        return f"🔊 当前音量: {int(player.volume * 100)}%"

    async def _handle_volume_mute(self, params: Dict) -> str:
        player = self._get_player()
        player.mute()
        return "🔇 已静音（音乐播放器）"

    async def _handle_volume_unmute(self, params: Dict) -> str:
        player = self._get_player()
        player.unmute()
        return f"🔊 已取消静音，当前音量: {int(player.volume * 100)}%"

    async def _handle_volume_up(self, params: Dict) -> str:
        player = self._get_player()
        player.volume_up()
        return f"🔊 音量增加，当前音量: {int(player.volume * 100)}%"

    async def _handle_volume_down(self, params: Dict) -> str:
        player = self._get_player()
        player.volume_down()
        return f"🔊 音量降低，当前音量: {int(player.volume * 100)}%"

    async def _handle_mode(self, params: Dict) -> str:
        player = self._get_player()
        mode = params.get("mode")
        
        if mode:
            try:
                play_mode = PlayMode(mode)
                player.set_play_mode(play_mode)
            except ValueError:
                player.toggle_play_mode()
        else:
            player.toggle_play_mode()
        
        mode_names = {
            PlayMode.SEQUENCE: "顺序播放",
            PlayMode.RANDOM: "随机播放",
            PlayMode.SINGLE_LOOP: "单曲循环",
            PlayMode.LIST_LOOP: "列表循环"
        }
        return f"🔀 播放模式: {mode_names.get(player.play_mode, player.play_mode.value)}"

    async def _handle_status(self, params: Dict) -> str:
        player = self._get_player()
        status = player.get_status()
        
        if status["current_song"]:
            song = status["current_song"]
            return (
                f"🎵 当前播放: {song['title']}\n"
                f"📊 状态: {'播放中' if status['is_playing'] else '已暂停'}\n"
                f"🔊 音量: {int(status['volume'] * 100)}%\n"
                f"🔀 模式: {status['play_mode']}"
            )
        return "🎵 当前未播放任何歌曲"

    async def _handle_playlist(self, params: Dict) -> str:
        player = self._get_player()
        action = params.get("action", "list")
        
        if action == "create":
            name = params.get("name", "新播放列表")
            playlist = player.create_playlist(name)
            return f"✅ 创建播放列表: {name}"
        
        elif action == "list":
            if not player.playlists:
                return "📭 暂无播放列表"
            result = "📁 播放列表:\n\n"
            for pl in player.playlists.values():
                result += f"• {pl.name} ({len(pl.songs)} 首)\n"
            return result
        
        return "❌ 未知操作"

    async def _handle_favorite(self, params: Dict) -> str:
        player = self._get_player()
        action = params.get("action", "list")
        
        if action == "add" and player.current_song:
            player.add_to_favorites(player.current_song.path)
            return f"❤️ 已收藏: {player.current_song.title}"
        
        elif action == "remove" and player.current_song:
            player.remove_from_favorites(player.current_song.path)
            return f"💔 已取消收藏: {player.current_song.title}"
        
        elif action == "list":
            if not player.favorites:
                return "💔 暂无收藏歌曲"
            result = f"❤️ 收藏列表 ({len(player.favorites)} 首):\n\n"
            for i, path in enumerate(player.favorites[:20], 1):
                result += f"{i}. {Path(path).stem}\n"
            return result
        
        return "❌ 未知操作"

    async def _handle_history(self, params: Dict) -> str:
        player = self._get_player()
        
        if not player.play_history:
            return "📜 暂无播放历史"
        
        result = f"📜 最近播放 ({len(player.play_history)} 首):\n\n"
        for i, path in enumerate(reversed(player.play_history[-20:]), 1):
            result += f"{i}. {Path(path).stem}\n"
        return result

    async def _handle_get_current_file(self, params: Dict) -> str:
        """获取当前播放的音乐文件路径"""
        player = self._get_player()
        status = player.get_status()
        
        if not status.get("is_playing"):
            return ""
        
        current_song = status.get("current_song")
        if current_song:
            if hasattr(current_song, 'path'):
                return current_song.path
            elif isinstance(current_song, dict):
                return current_song.get("path", "")
            elif isinstance(current_song, str):
                return current_song
        
        return ""

    async def _handle_open_player(self, params: Dict) -> str:
        """打开音乐播放器窗口"""
        self._show_music_minimized_item()
        player = self._get_player()
        songs = player.get_cached_songs()
        if songs:
            return f"🎵 音乐播放器已打开\n\n📋 播放列表共 {len(songs)} 首歌曲"
        else:
            songs = player.scan_music_library()
            if songs:
                return f"🎵 音乐播放器已打开\n\n📋 播放列表共 {len(songs)} 首歌曲"
            return "🎵 音乐播放器已打开\n\n⚠️ 音乐库暂无歌曲，请先扫描音乐库"

    async def _handle_scan_library(self, params: Dict) -> str:
        """重新扫描音乐库"""
        music_library = self._get_music_library()
        self._send_message_to_chat(f"🔍 正在扫描音乐库...\n\n📁 路径: {music_library}")
        
        player = self._get_player()
        songs = player.scan_music_library(force=True)
        
        if not songs:
            return f"❌ 扫描完成，未找到音乐文件\n\n📁 音乐库路径: {music_library}\n\n请确保音乐库路径下有支持的音乐文件（MP3、WAV、FLAC、M4A、OGG、WMA、NCM）"
        
        return f"✅ 音乐库扫描完成\n\n🎵 共找到 {len(songs)} 首歌曲\n\n前10首:\n" + "\n".join([f"  {i+1}. {s.title}" for i, s in enumerate(songs[:10])])

    def get_status(self) -> Dict:
        status = super().get_status()
        player = self._get_player()
        player_status = player.get_status()
        status.update({
            "is_playing": player_status["is_playing"],
            "current_song": player_status["current_song"],
            "music_library": str(self._get_music_library()),
            "play_mode": player_status["play_mode"],
            "volume": player_status["volume"],
            "capabilities": [
                "play_audio", "stop_audio", "control_playback",
                "search_local_music", "playlist_management", "volume_control"
            ],
            "supported_formats": self.supported_formats,
        })
        return status

    async def handle_message(self, message: Message):
        logger.info(f"📨 收到来自 {message.from_agent} 的消息: {message.message_type}")

        if message.message_type == "play_request":
            data = message.data or {}
            result = await self._handle_play(data)
            await self.send_message(
                to_agent=message.from_agent,
                message_type="play_response",
                content=result
            )

        elif message.message_type == "stop_request":
            result = await self._handle_stop({})
            await self.send_message(
                to_agent=message.from_agent,
                message_type="stop_response",
                content=result
            )
