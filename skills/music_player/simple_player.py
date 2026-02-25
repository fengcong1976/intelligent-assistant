"""
简化版音乐播放器
只支持播放用户提供的链接或本地音频文件
"""
import asyncio
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional
from loguru import logger


class SimpleMusicPlayer:
    """简化版音乐播放器"""

    def __init__(self):
        self.current_process = None
        self.current_url = None
        self.is_playing = False
        self.current_title = ""

    async def play(self, source: str, title: str = "") -> str:
        """
        播放音频

        Args:
            source: 音频链接或本地文件路径
            title: 歌曲标题

        Returns:
            播放结果信息
        """
        try:
            # 停止当前播放
            await self.stop()

            self.current_title = title or "未知歌曲"
            self.current_url = source

            # 判断是本地文件还是网络链接
            if source.startswith(('http://', 'https://')):
                return await self._play_url(source, title)
            else:
                return await self._play_local(source, title)

        except Exception as e:
            logger.error(f"播放失败: {e}")
            return f"❌ 播放失败: {str(e)}"

    async def _play_url(self, url: str, title: str) -> str:
        """播放网络音频"""
        try:
            system = platform.system()

            if system == "Windows":
                # Windows: 使用默认浏览器或媒体播放器
                # 尝试使用 Windows Media Player
                try:
                    cmd = f'start wmplayer "{url}"'
                    subprocess.Popen(cmd, shell=True)
                    self.is_playing = True
                    return f"🎵 正在播放: {title}\n🔗 {url[:60]}..."
                except:
                    # 回退到浏览器
                    webbrowser.open(url)
                    return f"🎵 正在浏览器播放: {title}\n🔗 {url[:60]}..."

            elif system == "Darwin":  # macOS
                # macOS: 使用 afplay 或浏览器
                cmd = ["afplay", url]
                self.current_process = subprocess.Popen(cmd)
                self.is_playing = True
                return f"🎵 正在播放: {title}\n🔗 {url[:60]}..."

            else:  # Linux
                # Linux: 尝试多种播放器
                players = [
                    ["mpv", "--no-video", url],
                    ["mplayer", url],
                    ["ffplay", "-nodisp", "-autoexit", url],
                    ["cvlc", "--play-and-exit", url],
                ]

                for player_cmd in players:
                    try:
                        self.current_process = subprocess.Popen(
                            player_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        self.is_playing = True
                        return f"🎵 正在播放: {title}\n🔗 {url[:60]}..."
                    except FileNotFoundError:
                        continue

                # 如果都没有，使用浏览器
                webbrowser.open(url)
                return f"🎵 已在浏览器打开: {title}\n🔗 {url[:60]}..."

        except Exception as e:
            logger.error(f"播放链接失败: {e}")
            # 回退到浏览器
            webbrowser.open(url)
            return f"🎵 已在浏览器打开: {title}\n🔗 {url[:60]}..."

    async def _play_local(self, file_path: str, title: str) -> str:
        """播放本地音频文件"""
        try:
            path = Path(file_path)

            if not path.exists():
                return f"❌ 文件不存在: {file_path}"

            if not path.suffix.lower() in ['.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg']:
                return f"❌ 不支持的音频格式: {path.suffix}"

            system = platform.system()
            full_path = str(path.absolute())

            if system == "Windows":
                # Windows: 使用默认程序打开
                cmd = f'start "" "{full_path}"'
                subprocess.Popen(cmd, shell=True)
                self.is_playing = True
                return f"🎵 正在播放本地文件: {title or path.name}"

            elif system == "Darwin":  # macOS
                cmd = ["afplay", full_path]
                self.current_process = subprocess.Popen(cmd)
                self.is_playing = True
                return f"🎵 正在播放本地文件: {title or path.name}"

            else:  # Linux
                players = [
                    ["mpv", "--no-video", full_path],
                    ["mplayer", full_path],
                    ["ffplay", "-nodisp", "-autoexit", full_path],
                    ["cvlc", "--play-and-exit", full_path],
                ]

                for player_cmd in players:
                    try:
                        self.current_process = subprocess.Popen(
                            player_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        self.is_playing = True
                        return f"🎵 正在播放本地文件: {title or path.name}"
                    except FileNotFoundError:
                        continue

                return f"❌ 未找到可用的音频播放器"

        except Exception as e:
            logger.error(f"播放本地文件失败: {e}")
            return f"❌ 播放失败: {str(e)}"

    async def stop(self) -> str:
        """停止播放"""
        try:
            if self.current_process:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=2)
                except:
                    self.current_process.kill()
                self.current_process = None

            self.is_playing = False
            return "⏹️ 已停止播放"

        except Exception as e:
            logger.error(f"停止播放失败: {e}")
            return f"❌ 停止失败: {str(e)}"

    async def pause(self) -> str:
        """暂停播放（仅部分播放器支持）"""
        # 简化版暂不支持暂停，直接返回提示
        if self.is_playing:
            return "⏸️ 暂停功能需要播放器支持，建议先停止再重新播放"
        return "ℹ️ 当前没有正在播放的音频"

    def get_status(self) -> dict:
        """获取播放状态"""
        return {
            "is_playing": self.is_playing,
            "current_title": self.current_title,
            "current_url": self.current_url,
        }


# 全局播放器实例
_player = SimpleMusicPlayer()


async def execute(action: str, **kwargs) -> str:
    """
    执行音乐播放操作

    Args:
        action: 操作类型 (play, stop, pause, status)
        source: 音频链接或文件路径 (play 时需要)
        title: 歌曲标题 (可选)

    Returns:
        操作结果
    """
    if action == "play":
        source = kwargs.get("source", "")
        title = kwargs.get("title", "")

        if not source:
            return "❌ 请提供音频链接或文件路径"

        return await _player.play(source, title)

    elif action == "stop":
        return await _player.stop()

    elif action == "pause":
        return await _player.pause()

    elif action == "status":
        status = _player.get_status()
        if status["is_playing"]:
            return f"🎵 正在播放: {status['current_title']}\n🔗 {status['current_url'][:60] if status['current_url'] else 'N/A'}..."
        else:
            return "ℹ️ 当前没有正在播放的音频"

    else:
        return f"❌ 不支持的操作: {action}"


# 测试代码
if __name__ == "__main__":
    async def test():
        print("="*60)
        print("简化版音乐播放器测试")
        print("="*60)

        # 测试播放网络音频
        print("\n1. 测试播放网络音频...")
        test_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        result = await execute("play", source=test_url, title="测试音频")
        print(result)

        # 等待几秒
        await asyncio.sleep(5)

        # 测试停止
        print("\n2. 测试停止播放...")
        result = await execute("stop")
        print(result)

        # 测试状态
        print("\n3. 测试获取状态...")
        result = await execute("status")
        print(result)

        print("\n" + "="*60)
        print("测试完成")

    asyncio.run(test())
