"""
Music Control Skill Executor
支持网易云音乐后台播放 - 使用 Pygame
"""
import asyncio
import subprocess
import os
import sys
import json
import urllib.request
import urllib.parse
import hashlib
import base64
import threading
import tempfile
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class PlayResult:
    success: bool
    message: str
    data: Optional[Dict] = None


class NeteaseMusicAPI:
    """网易云音乐 API 封装"""

    def __init__(self):
        self.session = None
        self.csrf_token = None
        self.is_logged_in = False

    def _create_request(self, url: str, data: Optional[bytes] = None, headers: Optional[Dict] = None) -> urllib.request.Request:
        """创建请求"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        }

        if headers:
            default_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=default_headers)

        if self.session:
            req.add_header('Cookie', self.session)

        return req

    def search_song(self, keyword: str, limit: int = 1) -> Optional[Dict]:
        """搜索歌曲"""
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            encoded_keyword = urllib.parse.quote(keyword)
            url = f"https://music.163.com/api/search/get/web?s={encoded_keyword}&type=1&offset=0&total=true&limit={limit}"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://music.163.com/',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Accept-Encoding': 'identity',
                }
            )

            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                data = response.read()
                result = json.loads(data.decode('utf-8'))
                if result.get('code') == 200 and result.get('result', {}).get('songs'):
                    songs = result['result']['songs']
                    if songs:
                        return songs[0]
            return None
        except Exception as e:
            logger.error(f"搜索歌曲失败: {e}")
            return None

    def get_song_url(self, song_id: int, br: int = 320000, cookie: str = None) -> Optional[str]:
        """获取歌曲播放链接"""
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 方法1: 使用官方 API 获取链接（支持登录）
            try:
                api_url = f"https://interface.music.163.com/eapi/song/enhance/player/url"
                params = {
                    'ids': f'[{song_id}]',
                    'br': br,
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://music.163.com/',
                    'Content-Type': 'application/x-www-form-urlencoded',
                }

                if cookie:
                    headers['Cookie'] = cookie
                    logger.info("使用登录凭证获取链接")

                data = urllib.parse.urlencode(params).encode('utf-8')
                req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')

                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    if result.get('code') == 200:
                        songs = result.get('data', [])
                        if songs and len(songs) > 0:
                            url = songs[0].get('url')
                            if url and 'null' not in url:
                                logger.info(f"✅ API 获取链接成功")
                                return url
            except Exception as e:
                logger.warning(f"API 获取链接失败: {e}")

            # 方法2: 使用 outer/url（不需要登录，但可能受限）
            url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
            req = self._create_request(url)

            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                final_url = response.geturl()
                if final_url and '404' not in final_url:
                    content_length = response.headers.get('Content-Length', '0')
                    if int(content_length) > 10000:
                        return final_url

            return None
        except Exception as e:
            logger.error(f"获取歌曲链接失败: {e}")
            return None


class MusicPlayer:
    """音乐播放器 - 使用 Pygame 实现后台播放"""

    def __init__(self):
        self.is_playing = False
        self._play_thread = None
        self._stop_event = threading.Event()
        self._temp_file = None
        self._pygame_initialized = False

    def _init_pygame(self):
        """初始化 Pygame"""
        if not self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self._pygame_initialized = True
                logger.info("Pygame 音频初始化成功")
            except Exception as e:
                logger.error(f"Pygame 初始化失败: {e}")

    def _download_audio(self, url: str) -> Optional[str]:
        """下载音频到临时文件"""
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            logger.info(f"下载音频到: {temp_path}")

            # 下载音频
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://music.163.com/',
                }
            )

            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                data = response.read()
                with open(temp_path, 'wb') as f:
                    f.write(data)
                logger.info(f"下载完成: {len(data)} 字节")

            return temp_path
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            return None

    def _play_audio(self, file_path: str, song_name: str):
        """在后台线程中播放音频"""
        try:
            import pygame

            self._init_pygame()

            # 加载并播放音乐
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(0.8)
            pygame.mixer.music.play()

            self.is_playing = True
            logger.info(f"✅ 开始播放: {song_name}")

            # 等待播放完成或停止信号
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                time.sleep(0.1)

            # 停止播放
            pygame.mixer.music.stop()
            self.is_playing = False
            logger.info(f"播放结束: {song_name}")

        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            self.is_playing = False

    async def play_url(self, url: str, song_name: str) -> bool:
        """播放音乐 URL - 后台播放"""
        try:
            await self.stop()

            logger.info(f"准备播放: {song_name}")

            # 下载音频
            temp_file = self._download_audio(url)
            if not temp_file:
                logger.error("下载音频失败")
                return False

            self._temp_file = temp_file
            self._stop_event.clear()

            # 在后台线程中播放
            self._play_thread = threading.Thread(
                target=self._play_audio,
                args=(temp_file, song_name),
                daemon=True
            )
            self._play_thread.start()

            # 等待一下确保播放开始
            await asyncio.sleep(0.5)

            if self.is_playing:
                return True
            else:
                logger.error("播放未能开始")
                return False

        except Exception as e:
            logger.error(f"播放失败: {e}")
            return False

    async def stop(self):
        """停止播放"""
        self._stop_event.set()
        self.is_playing = False

        # 停止 Pygame 音乐
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except:
            pass

        # 等待播放线程结束
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2)

        # 清理临时文件
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
                logger.info(f"清理临时文件: {self._temp_file}")
            except:
                pass
            self._temp_file = None

        logger.info("停止播放")

    async def toggle(self):
        """播放/暂停切换"""
        try:
            import pygame
            if self.is_playing:
                pygame.mixer.music.pause()
                self.is_playing = False
                return False
            else:
                pygame.mixer.music.unpause()
                self.is_playing = True
                return True
        except:
            return False


class MusicController:
    """音乐控制器"""

    def __init__(self, cookie: str = None):
        self.player = MusicPlayer()
        self.api = NeteaseMusicAPI()
        self.current_song = None
        self.current_artist = None
        self.cookie = cookie  # 登录凭证

    def set_cookie(self, cookie: str):
        """设置登录凭证"""
        self.cookie = cookie
        logger.info("✅ 已设置登录凭证")

    async def execute(self, action: str = "play", song_name: str = "", artist: str = "") -> PlayResult:
        """执行音乐控制"""
        logger.info(f"执行音乐控制: action={action}, song={song_name}")

        if action == "play" and song_name:
            search_keyword = song_name
            if artist:
                search_keyword = f"{artist} {song_name}"

            logger.info(f"搜索: {search_keyword}")
            song_info = self.api.search_song(search_keyword)

            if song_info:
                song_id = song_info.get('id')
                song_name_found = song_info.get('name', song_name)
                artists = song_info.get('artists', [])
                artist_name = artists[0].get('name', '') if artists else ''

                logger.info(f"找到歌曲: {song_name_found} - {artist_name} (ID: {song_id})")

                # 尝试获取不同品质的链接
                logger.info(f"正在获取歌曲播放链接...")
                for br in [320000, 192000, 128000]:
                    logger.info(f"尝试音质: {br}bps")
                    song_url = self.api.get_song_url(song_id, br, self.cookie)
                    logger.info(f"获取到的链接: {song_url}")

                    if song_url and '404' not in song_url:
                        logger.info(f"尝试播放: {song_url[:80]}...")
                        success = await self.player.play_url(song_url, song_name_found)
                        logger.info(f"播放结果: {success}")

                        if success:
                            self.current_song = song_name_found
                            self.current_artist = artist_name

                            song_display = f"《{song_name_found}》"
                            if artist_name:
                                song_display += f" - {artist_name}"

                            quality = "HQ" if br >= 320000 else "SQ" if br >= 192000 else "标准"
                            return PlayResult(True, f"🎵 [{quality}] 正在后台播放 {song_display}")
                    else:
                        logger.warning(f"无法获取 {br}bps 音质链接")

                return PlayResult(False, f"❌ 歌曲《{song_name_found}》暂无播放链接，可能需要 VIP 或登录")
            else:
                return PlayResult(False, f"❌ 未找到歌曲《{song_name}》，请尝试其他关键词")

        elif action == "toggle":
            is_playing = await self.player.toggle()
            if is_playing:
                return PlayResult(True, "⏯️ 继续播放")
            else:
                return PlayResult(True, "⏸️ 已暂停")

        elif action == "stop":
            await self.player.stop()
            return PlayResult(True, "⏹️ 已停止播放")

        elif action == "next":
            return PlayResult(False, "❌ 下一首功能暂不支持")

        elif action in ["volume_up", "volume_down"]:
            return PlayResult(True, "🔊 请使用系统音量控制调整音量")

        else:
            return PlayResult(False, f"❌ 不支持的操作: {action}")


# 全局控制器实例
_controller: Optional[MusicController] = None


async def execute(action: str = "play", song_name: str = "", artist: str = "", cookie: str = None) -> str:
    """执行音乐控制命令"""
    global _controller

    if _controller is None:
        _controller = MusicController(cookie=cookie)
    elif cookie:
        # 更新 cookie
        _controller.set_cookie(cookie)

    try:
        result = await _controller.execute(action=action, song_name=song_name, artist=artist)
        return result.message
    except Exception as e:
        return f"❌ 执行失败: {str(e)}"


# 测试代码
if __name__ == "__main__":
    async def test():
        print("🎵 测试音乐控制")
        result = await execute(action="play", song_name="茉莉花")
        print(result)
        await asyncio.sleep(30)
        await execute(action="stop")

    asyncio.run(test())
