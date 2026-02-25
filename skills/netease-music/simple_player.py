"""
Simple Music Player - 简化版音乐播放器
使用系统默认播放器播放网络音频
"""
import asyncio
import webbrowser
import urllib.request
import urllib.parse
import json
import ssl
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class SongInfo:
    """歌曲信息"""
    id: int
    name: str
    artist: str
    url: Optional[str] = None


class SimpleMusicPlayer:
    """简化版音乐播放器 - 使用浏览器播放"""

    def __init__(self):
        self.current_song: Optional[SongInfo] = None
        self.is_playing = False

    def search_song(self, keyword: str) -> Optional[SongInfo]:
        """搜索歌曲"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 使用网易云搜索 API
            encoded_keyword = urllib.parse.quote(keyword)
            url = f"https://music.163.com/api/search/get/web?csrf_token=&hlpretag=&hlposttag=&s={encoded_keyword}&type=1&offset=0&total=true&limit=10"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://music.163.com/',
                'Accept': 'application/json',
            }

            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))

                if data.get('code') == 200:
                    songs = data.get('result', {}).get('songs', [])
                    if songs:
                        song = songs[0]
                        return SongInfo(
                            id=song.get('id'),
                            name=song.get('name', ''),
                            artist=song.get('artists', [{}])[0].get('name', '')
                        )

            return None
        except Exception as e:
            logger.error(f"搜索歌曲失败: {e}")
            return None

    def get_song_url(self, song_id: int) -> Optional[str]:
        """获取歌曲播放链接"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 使用网易云外链播放器
            url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://music.163.com/',
            }

            req = urllib.request.Request(url, headers=headers, method='HEAD')

            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                final_url = response.geturl()
                if final_url and '404' not in final_url:
                    return final_url

            return None
        except Exception as e:
            logger.error(f"获取歌曲链接失败: {e}")
            return None

    def play(self, song_name: str, artist: str = "") -> str:
        """
        播放歌曲 - 使用浏览器打开网易云音乐页面

        Args:
            song_name: 歌曲名
            artist: 歌手名

        Returns:
            播放结果信息
        """
        try:
            # 搜索歌曲
            keyword = f"{artist} {song_name}" if artist else song_name
            logger.info(f"搜索: {keyword}")

            song_info = self.search_song(keyword)

            if not song_info:
                return f"❌ 未找到歌曲: {song_name}"

            self.current_song = song_info

            # 构建网易云音乐歌曲页面 URL
            song_url = f"https://music.163.com/#/song?id={song_info.id}"

            # 在浏览器中打开
            webbrowser.open(song_url)
            self.is_playing = True

            return f"🎵 正在播放: 《{song_info.name}》 - {song_info.artist}\n🔗 已在浏览器中打开网易云音乐"

        except Exception as e:
            logger.error(f"播放失败: {e}")
            return f"❌ 播放失败: {str(e)}"

    def stop(self) -> str:
        """停止播放"""
        self.is_playing = False
        return "⏹️ 已停止播放"

    def pause(self) -> str:
        """暂停/继续"""
        if self.is_playing:
            self.is_playing = False
            return "⏸️ 已暂停"
        else:
            self.is_playing = True
            return "▶️ 继续播放"


# 全局播放器实例
_player: Optional[SimpleMusicPlayer] = None


async def execute(action: str = "play", song_name: str = "", artist: str = "", cookie: str = None) -> str:
    """执行音乐控制命令"""
    global _player

    if _player is None:
        _player = SimpleMusicPlayer()

    try:
        if action == "play" and song_name:
            return _player.play(song_name, artist)
        elif action == "stop":
            return _player.stop()
        elif action == "toggle":
            return _player.pause()
        else:
            return f"❌ 不支持的操作: {action}"
    except Exception as e:
        logger.error(f"执行音乐命令失败: {e}")
        return f"❌ 执行失败: {str(e)}"
