"""
Music Player - 专业音乐播放器
支持播放控制、播放列表管理、音乐库浏览、歌词显示
"""
import os
import json
import random
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from loguru import logger

from .lyrics import Lyrics, LyricsParser, lyrics_manager

try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class PlayMode(Enum):
    """播放模式"""
    SEQUENCE = "sequence"      # 顺序播放
    RANDOM = "random"          # 随机播放
    SINGLE_LOOP = "single_loop"  # 单曲循环
    LIST_LOOP = "list_loop"    # 列表循环


@dataclass
class Song:
    """歌曲信息"""
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: int = 0  # 秒
    cover: str = ""
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        if not self.title:
            self.title = Path(self.path).stem
        if not self.artist:
            self.artist = "未知艺术家"
        if not self.album:
            self.album = "未知专辑"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Song':
        return cls(**data)


@dataclass
class Playlist:
    """播放列表"""
    id: str
    name: str
    songs: List[Song] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_song(self, song: Song):
        self.songs.append(song)
        self.updated_at = datetime.now().isoformat()
    
    def remove_song(self, index: int):
        if 0 <= index < len(self.songs):
            self.songs.pop(index)
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "songs": [s.to_dict() for s in self.songs],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Playlist':
        songs = [Song.from_dict(s) for s in data.get("songs", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            songs=songs,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )


class MusicPlayer:
    """专业音乐播放器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    SUPPORTED_FORMATS = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".ncm"]
    
    def __new__(cls, music_library: Path = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, music_library: Path = None):
        if MusicPlayer._initialized:
            return
        
        self.music_library = music_library or Path.home() / "Music"
        self.playlists: Dict[str, Playlist] = {}
        self.current_playlist: Optional[Playlist] = None
        self.current_song_index: int = -1
        self.current_song: Optional[Song] = None
        self.play_mode = PlayMode.SEQUENCE
        self.volume: float = 0.7
        self.is_playing: bool = False
        self.position: int = 0
        self._is_decrypting: bool = False
        
        self.cached_songs: List[Song] = []
        self.last_song_path: Optional[str] = None
        self.last_position: int = 0
        
        self.current_lyrics: Optional[Lyrics] = None
        self.current_lyric_index: int = -1
        
        self.play_history: List[str] = []
        self.max_history = 100
        
        self.favorites: List[str] = []
        
        self._monitor_thread = None
        self._monitor_running = False
        
        self._on_song_change_callback = None
        
        self._load_data()
        self._start_monitor()
        
        MusicPlayer._initialized = True
    
    def _start_monitor(self):
        """启动播放监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_playback(self):
        """监控播放状态，自动播放下一首"""
        import time
        was_playing = False
        skip_next_check = False
        
        while self._monitor_running:
            try:
                if PYGAME_AVAILABLE:
                    is_busy = pygame.mixer.music.get_busy()
                    
                    if was_playing and not is_busy and not self._is_decrypting:
                        if not skip_next_check:
                            if self.is_playing and self.play_mode != PlayMode.SINGLE_LOOP:
                                self.next_song()
                                skip_next_check = True
                            elif self.play_mode == PlayMode.SINGLE_LOOP and self.current_song:
                                self._play_audio(self.current_song.path)
                                self.is_playing = True
                                self._notify_song_change()
                                skip_next_check = True
                    
                    if is_busy:
                        skip_next_check = False
                    
                    was_playing = is_busy
                
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"播放监控错误: {e}")
                time.sleep(1)
    
    def stop_monitor(self):
        """停止播放监控"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.info("🎵 播放监控已停止")
    
    def set_on_song_change_callback(self, callback):
        """设置歌曲切换回调函数"""
        self._on_song_change_callback = callback
    
    def _notify_song_change(self):
        """通知歌曲切换"""
        if self._on_song_change_callback:
            try:
                self._on_song_change_callback(self.current_song)
            except Exception as e:
                logger.debug(f"歌曲切换回调错误: {e}")
    
    def _get_data_path(self) -> Path:
        """获取数据存储路径"""
        data_path = Path("./data/music_player")
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path
    
    def _load_data(self):
        """加载保存的数据"""
        data_path = self._get_data_path()
        
        playlists_file = data_path / "playlists.json"
        if playlists_file.exists():
            try:
                with open(playlists_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pl_data in data.get("playlists", []):
                        playlist = Playlist.from_dict(pl_data)
                        self.playlists[playlist.id] = playlist
            except Exception as e:
                logger.error(f"加载播放列表失败: {e}")
        
        history_file = data_path / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    self.play_history = json.load(f)
            except Exception as e:
                logger.error(f"加载播放历史失败: {e}")
        
        favorites_file = data_path / "favorites.json"
        if favorites_file.exists():
            try:
                with open(favorites_file, "r", encoding="utf-8") as f:
                    self.favorites = json.load(f)
            except Exception as e:
                logger.error(f"加载收藏失败: {e}")
        
        cached_songs_file = data_path / "cached_songs.json"
        if cached_songs_file.exists():
            try:
                with open(cached_songs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_songs = [Song.from_dict(s) for s in data.get("songs", [])]
                    self.last_song_path = data.get("last_song_path")
                    self.last_position = data.get("last_position", 0)
                    self.volume = data.get("volume", 0.7)
                    self.play_mode = PlayMode(data.get("play_mode", "sequence"))
            except Exception as e:
                logger.error(f"加载缓存歌曲失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        data_path = self._get_data_path()
        
        playlists_file = data_path / "playlists.json"
        try:
            data = {
                "playlists": [pl.to_dict() for pl in self.playlists.values()]
            }
            with open(playlists_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存播放列表失败: {e}")
        
        history_file = data_path / "history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.play_history[-self.max_history:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存播放历史失败: {e}")
        
        favorites_file = data_path / "favorites.json"
        try:
            with open(favorites_file, "w", encoding="utf-8") as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存收藏失败: {e}")
        
        cached_songs_file = data_path / "cached_songs.json"
        try:
            data = {
                "songs": [s.to_dict() for s in self.cached_songs],
                "last_song_path": self.last_song_path,
                "last_position": self.last_position,
                "volume": self.volume,
                "play_mode": self.play_mode.value
            }
            with open(cached_songs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存歌曲失败: {e}")
    
    def _get_audio_duration(self, file_path: str) -> int:
        """获取音频文件时长（秒）"""
        if PYGAME_AVAILABLE:
            try:
                sound = pygame.mixer.Sound(file_path)
                return int(sound.get_length())
            except Exception as e:
                logger.debug(f"pygame获取时长失败 {file_path}: {e}")
        
        try:
            import mutagen
            audio = mutagen.File(file_path)
            if audio is not None:
                return int(audio.info.length)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"mutagen获取时长失败 {file_path}: {e}")
        
        return 0

    def scan_music_library(self, force: bool = False) -> List[Song]:
        """扫描音乐库"""
        if not force and self.cached_songs:
            return self.cached_songs
        
        songs = []
        
        if not self.music_library.exists():
            logger.warning(f"音乐库目录不存在: {self.music_library}")
            return songs
        
        for audio_file in self.music_library.rglob("*"):
            if audio_file.suffix.lower() in self.SUPPORTED_FORMATS:
                try:
                    if audio_file.suffix.lower() == '.ncm':
                        song = Song(
                            path=str(audio_file),
                            title=audio_file.stem + " [NCM]",
                            duration=0,
                        )
                        songs.append(song)
                    else:
                        duration = self._get_audio_duration(str(audio_file))
                        song = Song(
                            path=str(audio_file),
                            title=audio_file.stem,
                            duration=duration,
                        )
                        songs.append(song)
                except Exception as e:
                    logger.error(f"读取文件信息失败 {audio_file}: {e}")
        
        self.cached_songs = songs
        self._save_data()
        return songs
    
    def get_cached_songs(self) -> List[Song]:
        """获取缓存的歌曲列表"""
        return self.cached_songs
    
    def get_last_played_song(self) -> Optional[Song]:
        """获取上次播放的歌曲"""
        logger.info(f"🎵 get_last_played_song(): last_song_path={self.last_song_path}")
        logger.info(f"🎵 cached_songs 数量: {len(self.cached_songs)}")
        if self.last_song_path:
            for i, song in enumerate(self.cached_songs):
                if song.path == self.last_song_path:
                    logger.info(f"🎵 找到匹配歌曲 [{i}]: {song.title}")
                    return song
        logger.info("🎵 未找到匹配的歌曲")
        return None
    
    def create_playlist(self, name: str) -> Playlist:
        """创建播放列表"""
        import uuid
        playlist_id = str(uuid.uuid4())[:8]
        playlist = Playlist(id=playlist_id, name=name)
        self.playlists[playlist_id] = playlist
        self._save_data()
        logger.info(f"✅ 创建播放列表: {name}")
        return playlist
    
    def delete_playlist(self, playlist_id: str):
        """删除播放列表"""
        if playlist_id in self.playlists:
            del self.playlists[playlist_id]
            self._save_data()
            logger.info(f"🗑️ 删除播放列表: {playlist_id}")
    
    def add_to_playlist(self, playlist_id: str, song: Song):
        """添加歌曲到播放列表"""
        if playlist_id in self.playlists:
            self.playlists[playlist_id].add_song(song)
            self._save_data()
            logger.info(f"➕ 添加歌曲到播放列表: {song.title}")
    
    def remove_from_playlist(self, playlist_id: str, index: int):
        """从播放列表移除歌曲"""
        if playlist_id in self.playlists:
            self.playlists[playlist_id].remove_song(index)
            self._save_data()
            logger.info(f"➖ 从播放列表移除歌曲")
    
    def play(self, song: Song = None, playlist_id: str = None, index: int = 0, position: int = 0):
        """播放歌曲"""
        if song:
            self.current_song = song
            self._add_to_history(song.path)
            for i, s in enumerate(self.cached_songs):
                if s.path == song.path:
                    self.current_song_index = i
                    break
        elif playlist_id and playlist_id in self.playlists:
            self.current_playlist = self.playlists[playlist_id]
            self.current_song_index = index
            if 0 <= index < len(self.current_playlist.songs):
                self.current_song = self.current_playlist.songs[index]
                self._add_to_history(self.current_song.path)
        
        if self.current_song:
            self._play_audio(self.current_song.path)
            self.is_playing = True
            self.position = position
            self.last_song_path = self.current_song.path
            self.last_position = position
            self._save_data()
            
            self._load_lyrics(self.current_song.path)
            self._notify_song_change()
            
            return True
        return False
    
    def _load_lyrics(self, audio_path: str):
        """加载歌词"""
        self.current_lyrics = lyrics_manager.get_lyrics(audio_path)
        self.current_lyric_index = -1
    
    def get_current_lyric(self) -> Optional[str]:
        """获取当前歌词"""
        if not self.current_lyrics:
            return None
        
        line, index = self.current_lyrics.get_line_at_time(self.position)
        if line:
            self.current_lyric_index = index
            return line.text
        return None
    
    def get_lyrics_context(self, before: int = 2, after: int = 3) -> List[tuple]:
        """获取歌词上下文（用于显示）"""
        if not self.current_lyrics:
            return []
        
        _, index = self.current_lyrics.get_line_at_time(self.position)
        return self.current_lyrics.get_context_lines(index, before, after)
    
    def _play_audio(self, file_path: str):
        """实际播放音频"""
        if file_path.lower().endswith('.ncm'):
            self._play_ncm_async(file_path)
            return
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                self.position = 0
                return
            except Exception as e:
                logger.error(f"pygame 播放失败: {e}")
        
        try:
            os.startfile(file_path)
            logger.info(f"使用系统播放器打开: {file_path}")
        except Exception as e:
            logger.error(f"播放失败: {e}")

    def _play_ncm_async(self, ncm_path: str):
        """异步解密并播放 NCM 文件"""
        from .ncm_decrypt import decrypt_ncm_async, get_cached_ncm, is_ncm_file
        
        if not is_ncm_file(ncm_path):
            logger.error(f"不是 NCM 文件: {ncm_path}")
            return
        
        cached = get_cached_ncm(ncm_path)
        if cached:
            logger.info(f"📦 使用缓存的解密文件: {cached}")
            self._play_audio(cached)
            return
        
        self._is_decrypting = True
        logger.info(f"🔓 正在解密 NCM 文件，请稍候...")
        
        def on_decrypt_complete(decrypted_path: Optional[str]):
            self._is_decrypting = False
            if decrypted_path:
                logger.info(f"✅ NCM 解密完成，开始播放")
                self._play_audio(decrypted_path)
            else:
                logger.error(f"❌ NCM 解密失败: {ncm_path}")
        
        decrypt_ncm_async(ncm_path, on_decrypt_complete)

    def get_playback_position(self) -> int:
        """获取当前播放位置（秒）"""
        if PYGAME_AVAILABLE:
            try:
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0:
                    return pos_ms // 1000
            except Exception:
                pass
        return self.position

    def is_music_playing(self) -> bool:
        """检查音乐是否正在播放"""
        if self._is_decrypting:
            return True
        if PYGAME_AVAILABLE:
            return pygame.mixer.music.get_busy()
        return self.is_playing

    def pause(self):
        """暂停播放"""
        if PYGAME_AVAILABLE and self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            if self.current_song:
                self.last_song_path = self.current_song.path
                self.last_position = self.position
                self._save_data()
            logger.info("⏸️ 暂停播放")
    
    def resume(self):
        """恢复播放"""
        logger.info(f"🎵 resume() 被调用: current_song={self.current_song.title if self.current_song else None}")
        if PYGAME_AVAILABLE:
            if self.current_song:
                try:
                    is_busy = pygame.mixer.music.get_busy()
                    logger.info(f"🎵 pygame.mixer.music.get_busy()={is_busy}, self.is_playing={self.is_playing}")
                    if is_busy and not self.is_playing:
                        pygame.mixer.music.unpause()
                        self.is_playing = True
                        logger.info(f"▶️ 恢复播放: {self.current_song.title}")
                    elif not is_busy:
                        logger.info(f"▶️ 重新播放: {self.current_song.title}")
                        self._play_audio(self.current_song.path)
                        self.is_playing = True
                    else:
                        logger.info("▶️ 已经在播放中")
                except Exception as e:
                    logger.warning(f"恢复播放失败，尝试重新播放: {e}")
                    self._play_audio(self.current_song.path)
                    self.is_playing = True
            else:
                logger.info("▶️ 没有当前歌曲，尝试播放最近的歌曲")
                last_song = self.get_last_played_song()
                logger.info(f"🎵 get_last_played_song()={last_song.title if last_song else None}")
                if last_song:
                    logger.info(f"🎵 调用 play(song=last_song)")
                    self.play(song=last_song)
                elif self.play_history:
                    last_song_path = self.play_history[0]
                    if last_song_path:
                        self._play_audio(last_song_path)
                else:
                    logger.warning("没有可播放的歌曲历史")
    
    def stop(self):
        """停止播放"""
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        
        if self.current_song:
            self.last_song_path = self.current_song.path
            self.last_position = 0
            self._save_data()
        
        self.is_playing = False
        self.position = 0
        logger.info("⏹️ 停止播放")
    
    def next_song(self):
        """下一首"""
        songs = self.cached_songs
        if self.current_playlist and self.current_playlist.songs:
            songs = self.current_playlist.songs
        
        if not songs:
            logger.warning("没有可播放的歌曲")
            self.is_playing = False
            return False
        
        if self.play_mode == PlayMode.RANDOM:
            self.current_song_index = random.randint(0, len(songs) - 1)
        elif self.play_mode == PlayMode.SINGLE_LOOP:
            if self.current_song:
                self._play_audio(self.current_song.path)
                self.is_playing = True
                logger.info(f"🔁 单曲循环: {self.current_song.title}")
                return True
        else:
            self.current_song_index += 1
            if self.current_song_index >= len(songs):
                if self.play_mode == PlayMode.LIST_LOOP:
                    self.current_song_index = 0
                else:
                    logger.info("播放列表已结束")
                    self.is_playing = False
                    return False
        
        if 0 <= self.current_song_index < len(songs):
            self.current_song = songs[self.current_song_index]
            self._play_audio(self.current_song.path)
            self._load_lyrics(self.current_song.path)
            self._add_to_history(self.current_song.path)
            self.is_playing = True
            self.last_song_path = self.current_song.path
            self._save_data()
            self._notify_song_change()
            logger.info(f"⏭️ 下一首: {self.current_song.title}")
            return True
        self.is_playing = False
        return False
    
    def previous_song(self):
        """上一首"""
        songs = self.cached_songs
        if self.current_playlist and self.current_playlist.songs:
            songs = self.current_playlist.songs
        
        if not songs:
            logger.warning("没有可播放的歌曲")
            return False
        
        self.current_song_index -= 1
        if self.current_song_index < 0:
            if self.play_mode == PlayMode.LIST_LOOP:
                self.current_song_index = len(songs) - 1
            else:
                self.current_song_index = 0
                return False
        
        if 0 <= self.current_song_index < len(songs):
            self.current_song = songs[self.current_song_index]
            self._play_audio(self.current_song.path)
            self._load_lyrics(self.current_song.path)
            self._add_to_history(self.current_song.path)
            self.is_playing = True
            self.last_song_path = self.current_song.path
            self._save_data()
            self._notify_song_change()
            logger.info(f"⏮️ 上一首: {self.current_song.title}")
            return True
        return False
    
    def set_volume(self, volume: float):
        """设置音量 (0.0 - 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self.volume)
        logger.info(f"🔊 音量: {int(self.volume * 100)}%")
    
    def volume_up(self, delta: float = 0.1):
        """增加音量"""
        self.set_volume(self.volume + delta)
    
    def volume_down(self, delta: float = 0.1):
        """降低音量"""
        self.set_volume(self.volume - delta)
    
    def mute(self):
        """静音"""
        self._previous_volume = self.volume
        self.set_volume(0)
    
    def unmute(self):
        """取消静音"""
        if hasattr(self, '_previous_volume') and self._previous_volume > 0:
            self.set_volume(self._previous_volume)
        else:
            self.set_volume(0.5)
    
    def set_play_mode(self, mode: PlayMode):
        """设置播放模式"""
        self.play_mode = mode
        self._save_data()
        mode_names = {
            PlayMode.SEQUENCE: "顺序播放",
            PlayMode.RANDOM: "随机播放",
            PlayMode.SINGLE_LOOP: "单曲循环",
            PlayMode.LIST_LOOP: "列表循环"
        }
        logger.info(f"🔀 播放模式: {mode_names.get(mode, mode.value)}")
    
    def toggle_play_mode(self):
        """切换播放模式"""
        modes = list(PlayMode)
        current_index = modes.index(self.play_mode)
        next_mode = modes[(current_index + 1) % len(modes)]
        self.set_play_mode(next_mode)
        return next_mode
    
    def _add_to_history(self, song_path: str):
        """添加到播放历史"""
        if song_path in self.play_history:
            self.play_history.remove(song_path)
        self.play_history.append(song_path)
        if len(self.play_history) > self.max_history:
            self.play_history = self.play_history[-self.max_history:]
        self._save_data()
    
    def add_to_favorites(self, song_path: str):
        """添加到收藏"""
        if song_path not in self.favorites:
            self.favorites.append(song_path)
            self._save_data()
            logger.info(f"❤️ 添加收藏: {Path(song_path).stem}")
    
    def remove_from_favorites(self, song_path: str):
        """移除收藏"""
        if song_path in self.favorites:
            self.favorites.remove(song_path)
            self._save_data()
            logger.info(f"💔 移除收藏: {Path(song_path).stem}")
    
    def is_favorite(self, song_path: str) -> bool:
        """检查是否已收藏"""
        return song_path in self.favorites
    
    def get_status(self) -> Dict[str, Any]:
        """获取播放器状态"""
        return {
            "is_playing": self.is_playing,
            "current_song": self.current_song.to_dict() if self.current_song else None,
            "current_song_index": self.current_song_index,
            "play_mode": self.play_mode.value,
            "volume": self.volume,
            "position": self.position,
            "playlist_count": len(self.playlists),
            "history_count": len(self.play_history),
            "favorites_count": len(self.favorites)
        }
