"""
Video Player - 视频播放器
支持常用视频格式播放和网络视频链接
"""
import os
import subprocess
import sys
import threading
import time
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from loguru import logger
from enum import Enum


def _find_vlc_dir() -> Optional[str]:
    """查找 VLC 目录（优先使用项目自带的）"""
    # 首先检查项目目录下的 vlc_libs
    project_dir = Path(__file__).parent.parent.parent.parent
    local_vlc = project_dir / "vlc_libs"
    if local_vlc.exists() and (local_vlc / "libvlc.dll").exists():
        return str(local_vlc)
    
    # 然后检查系统安装的 VLC
    possible_dirs = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        r"D:\Program Files\VideoLAN\VLC",
        r"D:\Program Files (x86)\VideoLAN\VLC",
        r"D:\VideoLAN\VLC",
        r"D:\VLC",
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(os.path.join(dir_path, "libvlc.dll")):
            return dir_path
    
    return None


# 在导入 vlc 之前设置环境变量
_vlc_dir = _find_vlc_dir()
if _vlc_dir:
    os.environ['PATH'] = _vlc_dir + os.pathsep + os.environ.get('PATH', '')
    os.environ['VLC_PLUGIN_PATH'] = os.path.join(_vlc_dir, 'plugins')
    logger.info(f"🎬 使用 VLC 目录: {_vlc_dir}")

# 导入独立播放器
try:
    from .standalone_player import (
        StandaloneVideoPlayer, VideoInfo, VideoPlayerThread,
        show_player, create_player_instance, get_player_instance
    )
    STANDALONE_PLAYER_AVAILABLE = True
    logger.info("✅ 独立视频播放器加载成功")
except ImportError as e:
    logger.warning(f"独立播放器不可用: {e}")
    STANDALONE_PLAYER_AVAILABLE = False
    StandaloneVideoPlayer = None
    VideoInfo = None
    VideoPlayerThread = None
    show_player = None
    create_player_instance = None
    get_player_instance = None


class PlayState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class Video:
    title: str
    path: Optional[Path] = None
    url: Optional[str] = None
    duration: float = 0
    size: int = 0
    is_online: bool = False
    
    def __post_init__(self):
        if self.path and isinstance(self.path, str):
            self.path = Path(self.path)
    
    @property
    def format(self) -> str:
        if self.is_online:
            return ".online"
        if self.path:
            return self.path.suffix.lower()
        return ""
    
    @property
    def display_title(self) -> str:
        if self.is_online:
            return f"[在线] {self.title}"
        return self.title


class VideoPlayer:
    """视频播放器 - 支持本地视频和网络视频链接"""
    
    SUPPORTED_FORMATS = [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"]
    
    # 支持的视频链接模式
    URL_PATTERNS = [
        r'^https?://[^\s]+\.(mp4|avi|mkv|mov|wmv|flv|webm|m4v|mpg|mpeg|3gp)(\?[^\s]*)?$',
        r'^https?://[^\s]+/video/[^\s]*$',
        r'^https?://[^\s]+/watch\?v=[^\s]*$',
        r'^https?://[^\s]+/v/[^\s]*$',
        r'^https?://[^\s]+\.m3u8(\?[^\s]*)?$',
        r'^https?://[^\s]+/stream/[^\s]*$',
    ]
    
    def __init__(self, video_library: Path = None):
        self.video_library = video_library or Path.home() / "Videos"
        self.current_video: Optional[Video] = None
        self.state = PlayState.STOPPED
        self.volume: float = 1.0
        self._process: Optional[subprocess.Popen] = None
        self._position: float = 0.0
        self._duration: float = 0.0
        self._video_list: List[Video] = []
        self._current_index: int = -1
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running: bool = False
        
        self._scan_video_library()
        logger.info(f"🎬 视频播放器已初始化，库中有 {len(self._video_list)} 个视频")
    
    def _is_video_url(self, text: str) -> bool:
        """检查是否为视频链接"""
        if not text:
            return False
        text = text.strip()
        for pattern in self.URL_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _extract_url_from_text(self, text: str) -> Optional[str]:
        """从文本中提取URL"""
        url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.]'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None
    
    def _scan_video_library(self):
        """扫描视频库"""
        self._video_list = []
        
        if not self.video_library.exists():
            logger.warning(f"视频库目录不存在: {self.video_library}")
            return
        
        for ext in self.SUPPORTED_FORMATS:
            for video_file in self.video_library.rglob(f"*{ext}"):
                try:
                    video = Video(
                        title=video_file.stem,
                        path=video_file,
                        size=video_file.stat().st_size
                    )
                    self._video_list.append(video)
                except Exception as e:
                    logger.debug(f"扫描视频失败: {video_file}: {e}")
        
        self._video_list.sort(key=lambda v: v.title.lower())
    
    def get_video_list(self) -> List[Video]:
        return self._video_list.copy()
    
    def search(self, query: str) -> List[Video]:
        """搜索视频"""
        query = query.lower()
        return [v for v in self._video_list if query in v.title.lower()]
    
    def play(self, video: Video = None, query: str = None, url: str = None) -> str:
        """播放视频 - 支持本地视频和网络链接"""
        # 优先处理URL
        if url:
            return self._play_url(url)
        
        # 检查query是否为URL
        if query and self._is_video_url(query):
            return self._play_url(query)
        
        # 从query中提取URL
        if query:
            extracted_url = self._extract_url_from_text(query)
            if extracted_url and self._is_video_url(extracted_url):
                return self._play_url(extracted_url)
        
        # 本地视频搜索
        if video is None and query:
            results = self.search(query)
            if not results:
                return f"❌ 未找到视频: {query}"
            video = results[0]
        
        if video is None:
            if self._video_list:
                video = self._video_list[0]
            else:
                return "❌ 视频库为空"
        
        # 播放本地视频
        return self._play_local(video)
    
    def _find_video_player(self) -> Optional[str]:
        """查找系统中可用的视频播放器 - 优先使用带GUI的播放器"""
        import shutil
        import glob
        
        # Windows 上优先检查带GUI的播放器（按优先级排序）
        if sys.platform == "win32":
            gui_players = [
                # C盘路径
                (r"C:\Program Files\VideoLAN\VLC\vlc.exe", "vlc"),
                (r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe", "vlc"),
                (r"C:\Program Files\PotPlayer\PotPlayer64.exe", "potplayer"),
                (r"C:\Program Files (x86)\PotPlayer\PotPlayer.exe", "potplayer"),
                (r"C:\Program Files\PotPlayer64\PotPlayer64.exe", "potplayer"),
                (r"C:\Program Files (x86)\PotPlayer64\PotPlayer64.exe", "potplayer"),
                (r"C:\Program Files\MPC-HC\mpc-hc64.exe", "mpc-hc"),
                (r"C:\Program Files (x86)\MPC-HC\mpc-hc.exe", "mpc-hc"),
                (r"C:\Program Files\MPC-BE\mpc-be64.exe", "mpc-be"),
                (r"C:\Program Files (x86)\MPC-BE\mpc-be.exe", "mpc-be"),
                # D盘路径
                (r"D:\Program Files\VideoLAN\VLC\vlc.exe", "vlc"),
                (r"D:\Program Files (x86)\VideoLAN\VLC\vlc.exe", "vlc"),
                (r"D:\VideoLAN\VLC\vlc.exe", "vlc"),
                (r"D:\VLC\vlc.exe", "vlc"),
                (r"D:\Program Files\PotPlayer\PotPlayer64.exe", "potplayer"),
                (r"D:\Program Files (x86)\PotPlayer\PotPlayer.exe", "potplayer"),
            ]
            
            for path_pattern, player_type in gui_players:
                matching_paths = glob.glob(path_pattern)
                if matching_paths:
                    logger.info(f"🎬 找到GUI播放器: {matching_paths[0]} ({player_type})")
                    return matching_paths[0]
        
        # 检查PATH中的播放器（优先GUI播放器）
        gui_players_in_path = ["vlc", "potplayer", "mpc-hc", "mpc-be"]
        for player in gui_players_in_path:
            path = shutil.which(player)
            if path:
                logger.info(f"🎬 找到GUI播放器: {path}")
                return path
        
        # 最后才使用命令行播放器
        cli_players = ["mpv", "ffplay"]
        for player in cli_players:
            path = shutil.which(player)
            if path:
                logger.info(f"🎬 找到CLI播放器: {path}")
                return path
        
        return None
    
    def _play_url(self, url: str, use_simple: bool = True) -> str:
        """播放网络视频链接 - 优先使用简单播放器"""
        try:
            self._stop_internal()
            
            # 尝试提取标题
            title = self._extract_title_from_url(url)
            
            # 优先使用简单播放器
            if use_simple and SIMPLE_PLAYER_AVAILABLE:
                try:
                    player = get_simple_player()
                    video_info = VideoInfo(title=title, url=url, is_online=True)
                    result = player.play(video_info)
                    
                    self.current_video = Video(
                        title=title,
                        url=url,
                        is_online=True
                    )
                    self.state = PlayState.PLAYING
                    
                    logger.info(f"🎬 使用简单播放器播放在线视频: {title}")
                    return result
                except Exception as e:
                    logger.warning(f"简单播放器失败，回退到外部播放器: {e}")
            
            # 尝试查找专业视频播放器
            player_path = self._find_video_player()
            
            if player_path:
                logger.info(f"🎬 使用外部播放器: {player_path}")
                player_lower = player_path.lower()
                
                if "vlc" in player_lower:
                    self._process = subprocess.Popen(
                        [player_path, url, "--play-and-exit"],
                        shell=False
                    )
                elif "potplayer" in player_lower:
                    self._process = subprocess.Popen(
                        [player_path, url],
                        shell=False
                    )
                elif "mpc-hc" in player_lower or "mpc-be" in player_lower:
                    self._process = subprocess.Popen(
                        [player_path, url],
                        shell=False
                    )
                elif "mpv" in player_lower:
                    self._process = subprocess.Popen(
                        [player_path, url, "--force-window=immediate", "--osc=yes"],
                        shell=False
                    )
                elif "ffplay" in player_lower:
                    self._process = subprocess.Popen(
                        [player_path, "-window_title", f"视频播放 - {title}", "-x", "1280", "-y", "720", url],
                        shell=False
                    )
                else:
                    self._process = subprocess.Popen(
                        [player_path, url],
                        shell=False
                    )
            else:
                # 回退到系统默认方式
                logger.info("🎬 未找到专业播放器，使用系统默认方式")
                if sys.platform == "win32":
                    self._process = subprocess.Popen(
                        ["cmd", "/c", "start", "", url],
                        shell=False
                    )
                elif sys.platform == "darwin":
                    self._process = subprocess.Popen(
                        ["open", url],
                        shell=False
                    )
                else:
                    self._process = subprocess.Popen(
                        ["xdg-open", url],
                        shell=False
                    )
            
            self.current_video = Video(
                title=title,
                url=url,
                is_online=True
            )
            self.state = PlayState.PLAYING
            
            player_name = "专业播放器" if player_path else "系统默认播放器"
            logger.info(f"🎬 播放在线视频: {title}")
            return f"▶️ 正在使用{player_name}播放: {title}\n🔗 {url[:80]}..."
            
        except Exception as e:
            logger.error(f"播放在线视频失败: {e}")
            return f"❌ 播放失败: {e}"
    
    def _extract_title_from_url(self, url: str) -> str:
        """从URL提取标题"""
        try:
            parsed = urllib.parse.urlparse(url)
            
            # YouTube风格
            if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
                return "YouTube视频"
            
            # Bilibili风格
            if 'bilibili.com' in parsed.netloc or 'b23.tv' in parsed.netloc:
                return "Bilibili视频"
            
            # 尝试从路径提取文件名
            path = parsed.path
            if path:
                filename = path.split('/')[-1]
                if filename:
                    # 移除扩展名
                    name = filename.split('.')[0]
                    if name:
                        # URL解码
                        return urllib.parse.unquote(name).replace('_', ' ').replace('-', ' ')
            
            # 使用域名
            return parsed.netloc
            
        except Exception:
            return "在线视频"
    
    def _play_local(self, video: Video) -> str:
        """播放本地视频"""
        if not video.path or not video.path.exists():
            return f"❌ 视频文件不存在: {video.path}"
        
        try:
            self._stop_internal()
            
            if sys.platform == "win32":
                self._process = subprocess.Popen(
                    ["cmd", "/c", "start", "", str(video.path)],
                    shell=False
                )
            elif sys.platform == "darwin":
                self._process = subprocess.Popen(
                    ["open", str(video.path)],
                    shell=False
                )
            else:
                self._process = subprocess.Popen(
                    ["xdg-open", str(video.path)],
                    shell=False
                )
            
            self.current_video = video
            self.state = PlayState.PLAYING
            self._current_index = self._video_list.index(video) if video in self._video_list else -1
            
            logger.info(f"🎬 播放视频: {video.title}")
            return f"▶️ 正在播放: {video.title}"
            
        except Exception as e:
            logger.error(f"播放视频失败: {e}")
            return f"❌ 播放失败: {e}"
    
    def _stop_internal(self):
        """内部停止方法"""
        # 停止简单播放器
        if SIMPLE_PLAYER_AVAILABLE:
            try:
                player = get_simple_player()
                if player.is_playing():
                    player.stop()
            except Exception:
                pass
        
        # 停止旧进程
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception:
                pass
            self._process = None
        
        self.state = PlayState.STOPPED
    
    def stop(self) -> str:
        """停止播放"""
        self._stop_internal()
        video_name = self.current_video.display_title if self.current_video else "未知"
        self.current_video = None
        logger.info(f"⏹️ 停止播放: {video_name}")
        return f"⏹️ 已停止播放: {video_name}"
    
    def pause(self) -> str:
        """暂停播放（提示用户在播放器中操作）"""
        return "💡 请在视频播放器中按空格键暂停"
    
    def resume(self) -> str:
        """继续播放"""
        if self.current_video:
            return "💡 请在视频播放器中按空格键继续播放"
        return "❌ 当前没有正在播放的视频"
    
    def next_video(self) -> str:
        """下一个视频"""
        if not self._video_list:
            return "❌ 视频库为空"
        
        self._current_index = (self._current_index + 1) % len(self._video_list)
        video = self._video_list[self._current_index]
        return self._play_local(video)
    
    def previous_video(self) -> str:
        """上一个视频"""
        if not self._video_list:
            return "❌ 视频库为空"
        
        self._current_index = (self._current_index - 1) % len(self._video_list)
        video = self._video_list[self._current_index]
        return self._play_local(video)
    
    def set_volume(self, volume: float):
        """设置音量（提示用户在系统或播放器中调节）"""
        self.volume = max(0.0, min(1.0, volume))
        logger.info(f"🔊 音量设置: {int(self.volume * 100)}%")
    
    def volume_up(self):
        """增加音量"""
        self.volume = min(1.0, self.volume + 0.1)
        logger.info(f"🔊 音量增加: {int(self.volume * 100)}%")
    
    def volume_down(self):
        """减小音量"""
        self.volume = max(0.0, self.volume - 0.1)
        logger.info(f"🔊 音量减小: {int(self.volume * 100)}%")
    
    def get_status(self) -> Dict:
        """获取播放状态"""
        return {
            "state": self.state.value,
            "current_video": self.current_video.display_title if self.current_video else None,
            "current_path": str(self.current_video.path) if self.current_video and self.current_video.path else None,
            "current_url": self.current_video.url if self.current_video else None,
            "is_online": self.current_video.is_online if self.current_video else False,
            "volume": int(self.volume * 100),
            "video_count": len(self._video_list),
            "current_index": self._current_index
        }
    
    def add_video_path(self, path: Path):
        """添加视频路径到库"""
        if path.exists() and path.suffix.lower() in self.SUPPORTED_FORMATS:
            video = Video(
                title=path.stem,
                path=path,
                size=path.stat().st_size
            )
            if video not in self._video_list:
                self._video_list.append(video)
                logger.info(f"🎬 添加视频: {video.title}")
    
    def set_video_library(self, path: Path):
        """设置视频库路径"""
        self.video_library = path
        self._scan_video_library()


video_player: Optional[VideoPlayer] = None


def get_video_player() -> VideoPlayer:
    global video_player
    if video_player is None:
        from ..config import settings
        video_dir = getattr(settings.directory, 'video_library', None)
        if video_dir:
            video_library = Path(video_dir)
        else:
            video_library = Path.home() / "Videos"
        video_player = VideoPlayer(video_library=video_library)
    return video_player
