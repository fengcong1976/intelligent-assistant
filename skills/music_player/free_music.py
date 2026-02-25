"""
Free Music Player - 免费网络音乐播放器
使用爬虫智能体搜索 MP3 链接，实现真正的音乐播放
"""
import asyncio
import webbrowser
import urllib.request
import urllib.parse
import json
import ssl
import re
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class SongInfo:
    """歌曲信息"""
    name: str
    artist: str
    url: Optional[str] = None
    source: str = ""
    mp3_url: Optional[str] = None  # 实际的 MP3 下载链接


class AudioPlayer:
    """音频播放器 - 使用系统命令播放音频"""

    def __init__(self):
        self.current_process = None
        self.is_playing = False

    def _get_player_command(self) -> Optional[str]:
        """获取系统音频播放器命令"""
        system = platform.system()

        if system == "Windows":
            # Windows 使用 PowerShell 和 Windows Media Player
            return "powershell"
        elif system == "Darwin":  # macOS
            # macOS 使用 afplay
            return "afplay"
        elif system == "Linux":
            # Linux 尝试多个播放器
            for cmd in ["mpv", "mplayer", "ffplay", "cvlc"]:
                if self._command_exists(cmd):
                    return cmd
        return None

    def _command_exists(self, cmd: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=False)
            return True
        except:
            return False

    async def play_url(self, url: str, title: str = "") -> str:
        """
        播放音频 URL

        Args:
            url: 音频文件 URL
            title: 歌曲标题

        Returns:
            播放结果信息
        """
        try:
            player = self._get_player_command()

            if not player:
                # 如果没有找到播放器，使用浏览器打开
                logger.info(f"🌐 未找到本地播放器，使用浏览器打开: {url}")
                webbrowser.open(url)
                return f"🎵 正在播放: {title}\n🌐 已在浏览器中打开"

            # 停止当前播放
            await self.stop()

            logger.info(f"🎵 使用 {player} 播放: {url}")

            if platform.system() == "Windows":
                # Windows 使用 PowerShell 播放
                # 使用 Start-Process 启动默认浏览器或媒体播放器
                cmd = [
                    "powershell",
                    "-Command",
                    f"Start-Process '{url}'"
                ]
            elif player == "afplay":  # macOS
                # 先下载文件再播放
                cmd = ["curl", "-L", "-o", "/tmp/temp_music.mp3", url, "&&", "afplay", "/tmp/temp_music.mp3"]
            elif player in ["mpv", "mplayer", "ffplay", "cvlc"]:
                # Linux 播放器直接播放 URL
                if player == "ffplay":
                    cmd = [player, "-nodisp", "-autoexit", url]
                elif player == "cvlc":
                    cmd = [player, "--play-and-exit", url]
                else:
                    cmd = [player, url]
            else:
                # 默认使用浏览器
                webbrowser.open(url)
                return f"🎵 正在播放: {title}\n🌐 已在浏览器中打开"

            # 启动播放进程
            if platform.system() == "Windows":
                # Windows 使用 shell=True 来执行 PowerShell 命令
                self.current_process = subprocess.Popen(" ".join(cmd), shell=True)
            else:
                self.current_process = subprocess.Popen(cmd)

            self.is_playing = True

            return f"🎵 正在播放: {title}\n🔗 来源: {url[:80]}..."

        except Exception as e:
            logger.error(f"❌ 播放失败: {e}")
            # 失败时回退到浏览器
            webbrowser.open(url)
            return f"🎵 正在播放: {title}\n🌐 已在浏览器中打开（本地播放器失败）"

    async def stop(self) -> str:
        """停止播放"""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            except:
                try:
                    self.current_process.kill()
                except:
                    pass
            self.current_process = None

        self.is_playing = False
        return "⏹️ 已停止播放"

    async def pause(self) -> str:
        """暂停/继续播放"""
        # 简单的实现：停止当前播放
        if self.is_playing:
            await self.stop()
            return "⏸️ 已暂停"
        else:
            return "▶️ 没有正在播放的歌曲"


class FreeMusicPlayer:
    """免费音乐播放器 - 使用爬虫智能体搜索 MP3 链接"""

    def __init__(self):
        self.current_song: Optional[SongInfo] = None
        self.is_playing = False
        self.playlist: List[SongInfo] = []
        self.audio_player = AudioPlayer()

    def _create_ssl_context(self):
        """创建 SSL 上下文"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def search_with_crawler(self, keyword: str) -> Optional[SongInfo]:
        """
        使用爬虫智能体搜索 MP3 链接
        """
        try:
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent.parent
            sys.path.insert(0, str(project_root))

            # 导入爬虫智能体
            from personal_agent.agents.crawler_agent import CrawlerAgent, CrawlTask
            from personal_agent.agents.base import Task

            logger.info(f"🕷️ 调用爬虫智能体搜索: {keyword}")

            # 创建爬虫智能体实例
            crawler = CrawlerAgent()

            # 创建搜索任务
            task = Task(
                type="search_mp3",
                content=f"搜索 MP3: {keyword}",
                params={"keyword": keyword}
            )

            # 执行任务
            result = await crawler.execute_task(task)

            # 解析结果，提取 MP3 链接
            lines = result.split('\n')

            for i, line in enumerate(lines):
                if line.strip().startswith('链接:') or line.strip().startswith('URL:'):
                    url = line.split(':', 1)[1].strip()

                    # 获取标题
                    title = keyword
                    if i > 0:
                        prev_line = lines[i-1]
                        if prev_line.strip() and not prev_line.strip().startswith('来源'):
                            if '.' in prev_line:
                                title = prev_line.split('.', 1)[1].strip()
                            else:
                                title = prev_line.strip()

                    logger.info(f"🎵 找到 MP3 资源: {title} -> {url}")

                    return SongInfo(
                        name=title,
                        artist="网络资源",
                        url=url,
                        source="CrawlerAgent",
                        mp3_url=url
                    )

            logger.warning(f"⚠️ 爬虫未找到 MP3 链接: {keyword}")
            return None

        except Exception as e:
            logger.error(f"❌ 爬虫搜索失败: {e}")
            return None

    async def play(self, song_name: str, artist: str = "") -> str:
        """
        播放歌曲 - 使用爬虫智能体搜索 MP3 链接并直接播放

        Args:
            song_name: 歌曲名
            artist: 歌手名

        Returns:
            播放结果信息
        """
        try:
            keyword = f"{artist} {song_name}" if artist else song_name
            logger.info(f"🎵 播放歌曲: {keyword}")

            # 首先尝试使用爬虫智能体搜索 MP3 链接
            song_info = await self.search_with_crawler(keyword)

            if not song_info:
                # 如果爬虫失败，使用 YouTube 搜索作为备用
                logger.info("🎵 爬虫搜索失败，使用 YouTube 搜索...")
                search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(keyword + ' audio')}"
                song_info = SongInfo(
                    name=keyword,
                    artist="YouTube",
                    url=search_url,
                    source="youtube_search"
                )

            self.current_song = song_info

            # 直接使用音频播放器播放
            if song_info.mp3_url or song_info.url:
                play_url = song_info.mp3_url or song_info.url
                result = await self.audio_player.play_url(play_url, song_info.name)
                self.is_playing = True
                return result
            else:
                return f"❌ 无法获取播放链接: {song_name}"

        except Exception as e:
            logger.error(f"播放失败: {e}")
            return f"❌ 播放失败: {str(e)}"

    async def stop(self) -> str:
        """停止播放"""
        self.is_playing = False
        return await self.audio_player.stop()

    async def pause(self) -> str:
        """暂停/继续"""
        result = await self.audio_player.pause()
        self.is_playing = self.audio_player.is_playing
        return result


# 全局播放器实例
_player: Optional[FreeMusicPlayer] = None


async def execute(action: str = "play", song_name: str = "", artist: str = "", cookie: str = None) -> str:
    """执行音乐控制命令"""
    global _player

    if _player is None:
        _player = FreeMusicPlayer()

    try:
        if action == "play" and song_name:
            return await _player.play(song_name, artist)
        elif action == "stop":
            return await _player.stop()
        elif action == "toggle":
            return await _player.pause()
        else:
            return f"❌ 不支持的操作: {action}"
    except Exception as e:
        logger.error(f"执行音乐命令失败: {e}")
        return f"❌ 执行失败: {str(e)}"
