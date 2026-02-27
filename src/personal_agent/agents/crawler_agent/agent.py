"""
Crawler Agent - 爬虫智能体
专门负责网络爬虫任务，搜索 MP3 链接、图片、视频等资源
使用国内可用的音乐源，并解析真实 MP3 链接
支持 Playwright 动态加载页面的视频提取
"""
import asyncio
import sys
import os
import re
import json
import ssl
import hashlib
import base64
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from ..base import BaseAgent, Task, Message

try:
    from ...config import Settings
except ImportError:
    Settings = None

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    source: str
    quality: str = "unknown"
    size: str = "unknown"
    duration: str = "unknown"
    extra_info: Dict = field(default_factory=dict)


@dataclass
class CrawlTask:
    """爬虫任务"""
    task_id: str
    keyword: str
    task_type: str  # mp3, video, image, etc.
    status: str = "pending"  # pending, running, completed, failed
    results: List[SearchResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: str = ""


class CrawlerAgent(BaseAgent):
    """
    爬虫智能体

    能力：
    - 搜索 MP3 音乐链接（使用国内可用源并解析真实链接）
    - 搜索视频链接
    - 搜索图片资源
    - 网页内容抓取
    - API 数据获取
    """
    
    PRIORITY = 4
    KEYWORD_MAPPINGS = {
        "搜索": ("web_search", {}),
        "搜索一下": ("web_search", {}),
        "查一下": ("web_search", {}),
        "查查": ("web_search", {}),
        "查找": ("web_search", {}),
        "查找一下": ("web_search", {}),
        "搜一下": ("web_search", {}),
        "帮我搜": ("web_search", {}),
        "帮我搜索": ("web_search", {}),
        "网上搜": ("web_search", {}),
        "网上搜索": ("web_search", {}),
        "百度一下": ("web_search", {}),
        "百度搜索": ("web_search", {}),
        "谷歌搜索": ("web_search", {}),
        "必应搜索": ("web_search", {}),
        "搜狗搜索": ("web_search", {}),
        "搜索网页": ("web_search", {}),
        "搜索网站": ("web_search", {}),
        "搜索资料": ("web_search", {}),
        "搜索信息": ("web_search", {}),
        "搜索新闻": ("web_search", {}),
        "搜索新闻": ("web_search", {}),
        "查新闻": ("web_search", {}),
        "看新闻": ("web_search", {}),
        "最新新闻": ("web_search", {}),
        "今日新闻": ("web_search", {}),
        "热点新闻": ("web_search", {}),
        "热搜": ("web_search", {}),
        "热搜榜": ("web_search", {}),
        "热搜话题": ("web_search", {}),
        "抓取网页": ("crawl_webpage", {}),
        "抓取网站": ("crawl_webpage", {}),
        "获取网页": ("crawl_webpage", {}),
        "读取网页": ("crawl_webpage", {}),
        "打开网页": ("crawl_webpage", {}),
        "访问网页": ("crawl_webpage", {}),
        "下载文件": ("file_download", {}),
        "下载": ("file_download", {}),
        "帮我下载": ("file_download", {}),
        "下载图片": ("file_download", {}),
        "下载视频": ("file_download", {}),
        "搜索图片": ("image_search", {}),
        "搜图片": ("image_search", {}),
        "找图片": ("image_search", {}),
        "查图片": ("image_search", {}),
        "搜索视频": ("video_search", {}),
        "搜视频": ("video_search", {}),
        "找视频": ("video_search", {}),
        "查视频": ("video_search", {}),
        "搜索MP3": ("search_mp3", {}),
        "搜MP3": ("search_mp3", {}),
        "搜索音乐下载": ("search_mp3", {}),
        "搜歌下载": ("search_mp3", {}),
        "提取链接": ("scrape_links", {}),
        "获取链接": ("scrape_links", {}),
        "抓取链接": ("scrape_links", {}),
        "提取视频链接": ("scrape_video_links", {}),
        "获取视频链接": ("scrape_video_links", {}),
        "抓取视频链接": ("scrape_video_links", {}),
        "获取mp4": ("scrape_video_links", {}),
        "获取mp4链接": ("scrape_video_links", {}),
        "提取mp4": ("scrape_video_links", {}),
        "提取mp4链接": ("scrape_video_links", {}),
        "抓取mp4": ("scrape_video_links", {}),
        "抓取mp4链接": ("scrape_video_links", {}),
        "解析视频": ("scrape_video_links", {}),
        "解析视频链接": ("scrape_video_links", {}),
        "解析mp4": ("scrape_video_links", {}),
        "解析mp4链接": ("scrape_video_links", {}),
        "获取视频": ("scrape_video_links", {}),
        "提取视频": ("scrape_video_links", {}),
        "抓取视频": ("scrape_video_links", {}),
        "爬取视频": ("scrape_video_links", {}),
        "爬取链接": ("scrape_links", {}),
        "爬取mp4": ("scrape_video_links", {}),
        "爬取网页": ("crawl_webpage", {}),
        "爬取网站": ("crawl_webpage", {}),
        "爬虫": ("crawl_webpage", {}),
        "爬取": ("crawl_webpage", {}),
        "抓取": ("crawl_webpage", {}),
        "获取": ("crawl_webpage", {}),
        "批量爬取": ("batch_scrape", {}),
        "批量抓取": ("batch_scrape", {}),
        "批量获取": ("batch_scrape", {}),
        "批量提取": ("batch_scrape", {}),
        "批量下载": ("batch_scrape", {}),
    }

    def __init__(self):
        super().__init__(
            name="crawler_agent",
            description="爬虫智能体 - 负责网络资源搜索和抓取"
        )

        # 注册能力
        self.register_capability(
            capability="search_web",
            description="搜索互联网获取信息。当你无法确定的信息（如实时新闻、最新数据），可以使用此工具查询。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题"
                    },
                    "location": {
                        "type": "string",
                        "description": "位置信息（可选），如'北京市朝阳区'，用于周边搜索"
                    }
                },
                "required": ["query"]
            },
            category="search"
        )
        
        self.register_capability("mp3_search", "MP3搜索")
        self.register_capability("video_search", "视频搜索")
        self.register_capability("image_search", "图片搜索")
        self.register_capability("web_crawl", "网页爬取")
        self.register_capability("api_fetch", "API获取")

        # 任务队列
        self.tasks: Dict[str, CrawlTask] = {}
        self.active_tasks: set = set()

        # 用户代理
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]

        logger.info("🕷️ 爬虫智能体已初始化")

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

    def _get_headers(self, referer: str = "") -> Dict[str, str]:
        """获取请求头"""
        import random
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if referer:
            headers['Referer'] = referer
        return headers

    def _create_ssl_context(self):
        """创建 SSL 上下文"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def execute_task(self, task: Task) -> Any:
        """
        执行爬虫任务
        """
        task_type = task.type
        params = task.params

        logger.info(f"🕷️ 执行爬虫任务: {task_type}")

        if task_type == "search_mp3":
            return await self._search_mp3(params)
        elif task_type == "search_video":
            return await self._search_video(params)
        elif task_type == "search_image":
            return await self._search_image(params)
        elif task_type == "crawl_webpage":
            return await self._crawl_webpage(params)
        elif task_type == "fetch_api":
            return await self._fetch_api(params)
        elif task_type == "get_task_status":
            return self._get_task_status(params)
        elif task_type == "get_task_results":
            return self._get_task_results(params)
        elif task_type in ("web_search", "search_web"):
            return await self._web_search(params)
        elif task_type == "general":
            return await self._handle_general(params)
        elif task_type == "scrape_links":
            return await self._scrape_links(params)
        elif task_type == "scrape_video_links":
            return await self._scrape_links(params)
        elif task_type == "scrape_m3u8_links":
            return await self._scrape_links(params)
        elif task_type == "extract_mp4_links":
            return await self._scrape_links(params)
        elif task_type == "extract_video_links":
            return await self._scrape_links(params)
        elif task_type == "scrape_mp4_links":
            return await self._scrape_links(params)
        elif task_type == "extract_page_links":
            return await self._extract_page_links(params)
        elif task_type == "scrape_page_links":
            return await self._extract_page_links(params)
        elif task_type == "batch_scrape":
            return await self._batch_scrape(params)
        elif task_type == "file_download":
            return await self._download_video(params)
        elif task_type == "agent_help":
            return self._get_help_info()
        else:
            return f"❌ 不支持的爬虫任务类型: {task_type}"
    
    async def _download_video(self, params: Dict) -> str:
        """下载视频：先抓取链接，再下载"""
        url = params.get("url", "")
        
        if not url:
            return "❌ 请提供视频页面 URL"
        
        # 清理 URL
        url = url.strip().strip('`').strip(',').strip()
        
        # 发送提示消息
        self._send_message_to_chat(f"📥 正在下载视频...\n\n🔗 URL: {url[:80]}{'...' if len(url) > 80 else ''}")
        
        logger.info(f"📥 下载视频: {url}")
        
        # 获取下载目录
        if Settings:
            settings = Settings()
            download_dir = str(settings.directory.get_download_dir())
        else:
            download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        # 优先尝试使用 yt-dlp（支持更多网站和加密视频）
        try:
            import subprocess
            import tempfile
            yt_dlp_path = shutil.which('yt-dlp')
            if yt_dlp_path:
                logger.info(f"📥 尝试使用 yt-dlp 下载...")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 使用临时目录下载（避免中文路径问题）
                temp_dir = tempfile.gettempdir()
                temp_output = os.path.join(temp_dir, f"video_{timestamp}.%(ext)s")
                
                cmd = [
                    yt_dlp_path,
                    '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    '--merge-output-format', 'mp4',
                    '-o', temp_output,
                    '--no-playlist',
                    '--progress',
                    '--newline',
                    '--no-check-certificates',
                    url
                ]
                
                logger.info(f"🎬 执行命令: yt-dlp -f best {url}")
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                
                stdout, _ = await process.communicate()
                
                if process.returncode == 0:
                    # 在临时目录查找下载的文件
                    for f in os.listdir(temp_dir):
                        if timestamp in f and f.endswith(('.mp4', '.mkv', '.webm')):
                            temp_filepath = os.path.join(temp_dir, f)
                            # 移动到目标目录
                            final_filepath = os.path.join(download_dir, f)
                            try:
                                shutil.move(temp_filepath, final_filepath)
                                filepath = final_filepath
                            except Exception as move_err:
                                logger.warning(f"移动文件失败: {move_err}，使用临时文件")
                                filepath = temp_filepath
                            
                            size = os.path.getsize(filepath)
                            logger.info(f"✅ yt-dlp 下载完成: {filepath} ({size / 1024 / 1024:.2f} MB)")
                            return f"✅ 视频下载完成！\n\n📁 文件路径: {filepath}\n📊 文件大小: {size / 1024 / 1024:.2f} MB"
                    return f"✅ yt-dlp 下载完成\n\n📁 下载目录: {download_dir}\n📁 临时目录: {temp_dir}"
                else:
                    error_msg = stdout.decode('utf-8', errors='ignore')[-500:] if stdout else "未知错误"
                    logger.warning(f"yt-dlp 下载失败: {error_msg}")
        except Exception as e:
            logger.warning(f"yt-dlp 不可用: {e}")
        
        # 回退到 Playwright 抓取
        logger.info("📥 yt-dlp 失败，回退到 Playwright 抓取...")
        
        # 1. 先抓取视频链接
        scrape_params = params.copy()
        scrape_params["link_type"] = "video"
        
        links_result = await self._scrape_links(scrape_params)
        
        # 检查是否获取到链接
        if links_result.startswith("❌"):
            return links_result
        
        # 提取链接
        import re
        links = re.findall(r'https?://[^\s]+', links_result)
        
        if not links:
            return f"❌ 未找到可下载的视频链接\n\n{links_result}"
        
        # 分类链接：优先 m3u8 > ts分片 > mp4
        m3u8_links = [l for l in links if '.m3u8' in l.lower()]
        mp4_links = [l for l in links if '.mp4' in l.lower() and '.m3u8' not in l.lower()]
        ts_links = [l for l in links if '.ts' in l.lower() and '.m3u8' not in l.lower()]
        
        # 过滤掉小文件（预览/广告），优先选择高清版本
        # 腾讯视频: f112007 = 1080p, f2 = 预览, gzc_1000xxx = 不同清晰度
        # 注意: MP4 链接可能是广告，TS 分片才是正片
        def get_quality_score(url):
            score = 0
            url_lower = url.lower()
            # 高清标识
            if 'f112007' in url_lower or 'f1080' in url_lower:
                score += 1000
            elif 'f720' in url_lower:
                score += 700
            elif 'f480' in url_lower:
                score += 400
            # 避免预览文件
            if '.f2.' in url_lower or '_f2' in url_lower:
                score -= 500
            # 避免广告
            if 'ad' in url_lower or 'promo' in url_lower:
                score -= 1000
            return score
        
        # 按质量排序 MP4 链接
        if mp4_links:
            mp4_links = sorted(mp4_links, key=get_quality_score, reverse=True)
            logger.info(f"📥 MP4 链接按质量排序，最佳: {mp4_links[0][:80]}...")
        
        # 过滤推断的 m3u8（通常无效），只保留从网络请求直接捕获的
        # 推断的地址通常包含 index.m3u8, playlist.m3u8 或以 .m3u8 结尾
        real_m3u8_links = [l for l in m3u8_links if 
                          'index.m3u8' not in l and 
                          'playlist.m3u8' not in l and
                          not l.rstrip('/').endswith('.m3u8')]
        
        # 优先使用 TS 分片（正片内容），MP4 可能是广告
        if len(ts_links) >= 3:
            logger.info(f"📥 找到 {len(ts_links)} 个 TS 分片（正片），优先合并下载")
            return await self._download_ts_segments(ts_links, links_result)
        # 其次选择真实捕获的 m3u8
        elif real_m3u8_links:
            video_url = real_m3u8_links[0]
            logger.info(f"📥 找到 m3u8 流媒体链接")
        # 高质量 mp4（可能是广告，需验证）
        elif mp4_links and get_quality_score(mp4_links[0]) > 0:
            video_url = mp4_links[0]
            logger.info(f"📥 找到高质量 MP4 链接（注意：可能是广告）")
        # 如果有少量 TS 分片，也尝试合并
        elif ts_links:
            logger.info(f"📥 找到 {len(ts_links)} 个 TS 分片，尝试合并下载")
            return await self._download_ts_segments(ts_links, links_result)
        # 普通 mp4
        elif mp4_links:
            video_url = mp4_links[0]
            logger.info(f"📥 找到 MP4 链接")
        # 最后尝试推断的 m3u8（通常无效）
        elif m3u8_links:
            video_url = m3u8_links[0]
            logger.info(f"📥 尝试推断的 m3u8 链接（可能无效）")
        else:
            video_url = links[0]
        
        logger.info(f"📥 准备下载: {video_url[:100]}...")
        
        # 2. 下载视频
        try:
            # 获取用户配置的下载目录
            if Settings:
                settings = Settings()
                download_dir = str(settings.directory.get_download_dir())
            else:
                download_dir = os.path.join(os.getcwd(), "downloads")
            os.makedirs(download_dir, exist_ok=True)
            logger.info(f"📥 下载目录: {download_dir}")
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if '.m3u8' in video_url.lower():
                filename = f"video_{timestamp}.m3u8"
            elif '.mp4' in video_url.lower():
                filename = f"video_{timestamp}.mp4"
            else:
                filename = f"video_{timestamp}.mp4"
            
            filepath = os.path.join(download_dir, filename)
            
            # 下载文件
            logger.info(f"📥 开始下载到: {filepath}")
            
            # 对于 m3u8 流媒体，使用 ffmpeg 下载
            if '.m3u8' in video_url.lower():
                return await self._download_m3u8(video_url, filepath, links_result)
            
            req = urllib.request.Request(video_url, headers=self._get_headers())
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=300, context=self._create_ssl_context())
            )
            
            # 获取文件大小
            file_size = response.getheader('Content-Length')
            if file_size:
                file_size = int(file_size)
                logger.info(f"📥 文件大小: {file_size / 1024 / 1024:.2f} MB")
            
            # 写入文件
            with open(filepath, 'wb') as f:
                while True:
                    chunk = await loop.run_in_executor(None, response.read, 8192)
                    if not chunk:
                        break
                    f.write(chunk)
            
            actual_size = os.path.getsize(filepath)
            logger.info(f"✅ 下载完成: {filepath} ({actual_size / 1024 / 1024:.2f} MB)")
            
            return f"✅ 视频下载完成！\n\n📁 文件路径: {filepath}\n📊 文件大小: {actual_size / 1024 / 1024:.2f} MB\n\n🔗 原始链接:\n{video_url[:100]}..."
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return f"❌ 下载失败: {str(e)}\n\n🔗 找到的视频链接:\n{links_result}"
    
    async def _download_m3u8(self, m3u8_url: str, filepath: str, links_result: str) -> str:
        """使用 ffmpeg 下载 m3u8 流媒体"""
        import shutil
        
        # 检查 ffmpeg 是否可用
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            return f"⚠️ m3u8 流媒体需要 ffmpeg 支持\n\n请先安装 ffmpeg:\n• Windows: winget install ffmpeg\n• Mac: brew install ffmpeg\n• Linux: apt install ffmpeg\n\n🔗 m3u8 链接:\n{m3u8_url[:100]}...\n\n📋 所有找到的链接:\n{links_result}"
        
        # 修改输出文件名为 mp4
        if filepath.endswith('.m3u8'):
            filepath = filepath[:-5] + '.mp4'
        
        logger.info(f"📥 使用 ffmpeg 下载 m3u8: {filepath}")
        
        try:
            import subprocess
            
            # 构建 ffmpeg 命令
            cmd = [
                ffmpeg_path,
                '-i', m3u8_url,
                '-c', 'copy',  # 直接复制流，不重新编码
                '-bsf:a', 'aac_adtstoasc',  # 修复 AAC 音频
                '-y',  # 覆盖已存在的文件
                filepath
            ]
            
            logger.info(f"🎬 执行命令: ffmpeg -i {m3u8_url[:50]}... -c copy {filepath}")
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                actual_size = os.path.getsize(filepath)
                logger.info(f"✅ m3u8 下载完成: {filepath} ({actual_size / 1024 / 1024:.2f} MB)")
                return f"✅ 视频下载完成！\n\n📁 文件路径: {filepath}\n📊 文件大小: {actual_size / 1024 / 1024:.2f} MB\n\n🔗 m3u8 链接:\n{m3u8_url[:100]}..."
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')[-500:]
                logger.error(f"ffmpeg 下载失败: {error_msg}")
                return f"❌ ffmpeg 下载失败\n\n错误信息: {error_msg}\n\n🔗 m3u8 链接:\n{m3u8_url[:100]}...\n\n📋 所有找到的链接:\n{links_result}"
                
        except Exception as e:
            logger.error(f"m3u8 下载失败: {e}")
            return f"❌ m3u8 下载失败: {str(e)}\n\n🔗 m3u8 链接:\n{m3u8_url[:100]}...\n\n📋 所有找到的链接:\n{links_result}"
    
    async def _download_ts_segments(self, ts_links: list, links_result: str) -> str:
        """下载并合并 TS 分片"""
        from datetime import datetime
        import shutil
        
        # 检查 ffmpeg 是否可用
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            return f"⚠️ TS 分片合并需要 ffmpeg 支持\n\n请先安装 ffmpeg:\n• Windows: winget install ffmpeg\n• Mac: brew install ffmpeg\n• Linux: apt install ffmpeg\n\n📋 找到 {len(ts_links)} 个 TS 分片链接"
        
        # 获取用户配置的下载目录
        if Settings:
            settings = Settings()
            download_dir = str(settings.directory.get_download_dir())
        else:
            download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"📥 下载目录: {download_dir}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(download_dir, f"ts_temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        output_file = os.path.join(download_dir, f"video_{timestamp}.mp4")
        
        logger.info(f"📥 开始下载 {len(ts_links)} 个 TS 分片...")
        
        try:
            # 按 index 排序
            def get_index(url):
                match = re.search(r'index=(\d+)', url)
                if match:
                    return int(match.group(1))
                match = re.search(r'/(\d+)_', url)
                if match:
                    return int(match.group(1))
                return 0
            
            sorted_links = sorted(ts_links, key=get_index)
            
            # 去重 - 按 URL 基础路径去重
            seen_bases = set()
            unique_links = []
            for link in sorted_links:
                # 提取基础路径（不含 token 等参数）
                base_match = re.match(r'(https?://[^?]+)', link)
                if base_match:
                    base = base_match.group(1)
                    # 提取分片编号
                    num_match = re.search(r'/(\d+)_gzc_', base)
                    if num_match:
                        num = num_match.group(1)
                        if num not in seen_bases:
                            seen_bases.add(num)
                            unique_links.append(link)
            
            sorted_links = unique_links if unique_links else sorted_links
            logger.info(f"📥 去重后 {len(sorted_links)} 个分片")
            
            # 下载所有分片
            downloaded_files = []
            loop = asyncio.get_event_loop()
            
            max_segments = 500  # 增加到500个分片
            for i, ts_url in enumerate(sorted_links[:max_segments]):
                try:
                    ts_file = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                    
                    req = urllib.request.Request(ts_url, headers=self._get_headers())
                    response = await loop.run_in_executor(
                        None,
                        lambda u=ts_url: urllib.request.urlopen(
                            urllib.request.Request(u, headers=self._get_headers()),
                            timeout=30,
                            context=self._create_ssl_context()
                        )
                    )
                    
                    with open(ts_file, 'wb') as f:
                        f.write(response.read())
                    
                    downloaded_files.append(ts_file)
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"📥 已下载 {i + 1}/{len(sorted_links[:max_segments])} 个分片")
                        
                except Exception as e:
                    logger.warning(f"下载分片 {i} 失败: {e}")
            
            if not downloaded_files:
                return f"❌ 所有 TS 分片下载失败\n\n📋 找到的链接:\n{links_result}"
            
            logger.info(f"📥 下载完成，共 {len(downloaded_files)} 个分片，开始合并...")
            
            # 创建合并列表文件
            list_file = os.path.join(temp_dir, "filelist.txt")
            with open(list_file, 'w', encoding='utf-8') as f:
                for ts_file in downloaded_files:
                    f.write(f"file '{ts_file}'\n")
            
            # 使用 ffmpeg 合并
            cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',
                output_file
            ]
            
            logger.info(f"🎬 使用 ffmpeg 合并分片...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            if process.returncode == 0:
                actual_size = os.path.getsize(output_file)
                logger.info(f"✅ TS 合并完成: {output_file} ({actual_size / 1024 / 1024:.2f} MB)")
                return f"✅ 视频下载完成！\n\n📁 文件路径: {output_file}\n📊 文件大小: {actual_size / 1024 / 1024:.2f} MB\n📦 合并分片: {len(downloaded_files)} 个"
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')[-500:]
                logger.error(f"ffmpeg 合并失败: {error_msg}")
                return f"❌ 分片合并失败\n\n错误信息: {error_msg}"
                
        except Exception as e:
            logger.error(f"TS 下载合并失败: {e}")
            return f"❌ TS 分片下载合并失败: {str(e)}\n\n📋 找到的链接:\n{links_result}"
    
    async def _batch_scrape(self, params: Dict) -> str:
        """批量爬取视频链接"""
        url_template = params.get("url", "") or params.get("url_template", "")
        start_id = params.get("start_id", 0)
        end_id = params.get("end_id", 0)
        link_type = params.get("link_type", "mp4")
        
        # 从 URL 中提取模板和 ID 范围
        if url_template and not start_id:
            id_match = re.search(r'/(\d+)(?:[/\?]|$)', url_template)
            if id_match:
                start_id = int(id_match.group(1))
                # 如果没有指定结束 ID，默认爬取 10 个
                if not end_id:
                    end_id = start_id + 9
        
        if not url_template or not start_id or not end_id:
            return "❌ 批量爬取需要提供 URL 模板和 ID 范围\n\n格式：从 https://example.com/video/138009 到 https://example.com/video/138200"
        
        if start_id > end_id:
            return f"❌ 起始 ID ({start_id}) 不能大于结束 ID ({end_id})"
        
        # 限制批量爬取数量
        max_count = 50
        if end_id - start_id + 1 > max_count:
            end_id = start_id + max_count - 1
            logger.warning(f"批量爬取数量限制为 {max_count} 个")
        
        # 发送提示消息
        count = end_id - start_id + 1
        self._send_message_to_chat(f"🔄 开始批量爬取...\n\n📊 数量: {count} 个页面\n🔗 从 {start_id} 到 {end_id}\n📁 类型: {link_type}")
        
        logger.info(f"🔄 批量爬取: {url_template} 从 {start_id} 到 {end_id}")
        
        # 生成 URL 列表
        base_url = re.sub(r'/\d+(/?)$', '/{id}\\1', url_template)
        if '{id}' not in base_url:
            base_url = url_template.rsplit('/', 1)[0] + '/{id}'
        
        all_results = []
        failed_ids = []
        
        for video_id in range(start_id, end_id + 1):
            url = base_url.replace('{id}', str(video_id))
            logger.info(f"🔄 爬取: {url}")
            
            try:
                # 使用 Playwright 动态抓取
                if PLAYWRIGHT_AVAILABLE:
                    links, error = await self._scrape_dynamic_video(url)
                    if links:
                        # 过滤 MP4 链接
                        if link_type.lower() == "mp4":
                            links = [l for l in links if '.mp4' in l.lower()]
                        elif link_type.lower() == "m3u8":
                            links = [l for l in links if '.m3u8' in l.lower()]
                        
                        if links:
                            all_results.append({
                                "id": video_id,
                                "url": url,
                                "links": links
                            })
                            continue
                
                # 如果 Playwright 失败，尝试静态抓取
                req = urllib.request.Request(url, headers=self._get_headers())
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda u=url: urllib.request.urlopen(
                        urllib.request.Request(u, headers=self._get_headers()),
                        timeout=30,
                        context=self._create_ssl_context()
                    )
                )
                html = response.read().decode('utf-8', errors='ignore')
                
                # 提取视频链接
                video_patterns = [
                    r'https?://[^\s<>"\']+\.(?:mp4|m3u8)[^\s<>"\']*',
                ]
                
                links = []
                for pattern in video_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for m in matches:
                        m = m.strip('"\'')
                        if link_type.lower() == "mp4" and '.mp4' in m.lower():
                            links.append(m)
                        elif link_type.lower() == "m3u8" and '.m3u8' in m.lower():
                            links.append(m)
                        elif link_type.lower() not in ["mp4", "m3u8"]:
                            links.append(m)
                
                if links:
                    all_results.append({
                        "id": video_id,
                        "url": url,
                        "links": list(dict.fromkeys(links))
                    })
                else:
                    failed_ids.append(video_id)
                    
            except Exception as e:
                logger.warning(f"爬取 {url} 失败: {e}")
                failed_ids.append(video_id)
            
            # 添加延迟避免被封
            await asyncio.sleep(1)
        
        # 格式化输出
        if not all_results:
            return f"❌ 批量爬取失败，共 {len(failed_ids)} 个页面无法访问"
        
        result_text = f"🔄 批量爬取完成\n\n"
        result_text += f"📊 统计：\n"
        result_text += f"• 成功：{len(all_results)} 个\n"
        result_text += f"• 失败：{len(failed_ids)} 个\n"
        result_text += f"• ID 范围：{start_id} - {end_id}\n\n"
        
        result_text += f"🎬 视频链接：\n\n"
        for item in all_results:
            result_text += f"【ID: {item['id']}】{item['url']}\n"
            for i, link in enumerate(item['links'][:3], 1):
                result_text += f"  {i}. {link}\n"
            if len(item['links']) > 3:
                result_text += f"  ... 还有 {len(item['links']) - 3} 个链接\n"
            result_text += "\n"
        
        if failed_ids and len(failed_ids) <= 10:
            result_text += f"\n⚠️ 失败的 ID：{', '.join(map(str, failed_ids))}"
        
        return result_text
    
    async def _extract_page_links(self, params: Dict) -> str:
        """提取网页中的有效链接，过滤广告等垃圾内容"""
        url = params.get("url", "")
        
        if not url:
            return "❌ 请提供网页 URL"
        
        # 清理 URL
        url = url.strip().strip('`').strip(',').strip()
        
        logger.info(f"🔗 提取页面链接: {url}")
        
        # 广告和垃圾链接关键词
        ad_keywords = [
            'ad', 'ads', 'adv', 'advert', 'advertising', 'advertisement',
            'banner', 'popup', 'popunder', 'sponsor', 'sponsored',
            'analytics', 'tracking', 'tracker', 'pixel', 'beacon',
            'doubleclick', 'googlesyndication', 'googleadservices',
            'facebook.com/tr', 'facebook.com/plugins',
            'twitter.com/i/ads', 'linkedin.com/pixel',
            'criteo', 'outbrain', 'taboola', 'revcontent',
            'aff', 'affiliate', 'promo', 'promotion',
            'click', 'redirect', 'go.php', 'jump.php', 'link.php',
            'count', 'stat', 'tongji', 'cnzz', 'baidu.com/hm',
            'google-analytics', 'googletagmanager',
        ]
        
        # 无效链接后缀
        invalid_extensions = [
            '.css', '.js', '.json', '.xml', '.rss', '.atom',
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp',
            '.woff', '.woff2', '.ttf', '.eot', '.otf',
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.7z', '.tar', '.gz',
        ]
        
        # 无效链接模式
        invalid_patterns = [
            r'^javascript:', r'^mailto:', r'^tel:', r'^#',
            r'^data:', r'^blob:', r'^about:',
        ]
        
        # 优先使用 Playwright 动态抓取
        if PLAYWRIGHT_AVAILABLE:
            logger.info(f"🎭 使用 Playwright 动态提取页面链接...")
            dynamic_links = await self._extract_links_with_playwright(url, ad_keywords, invalid_extensions, invalid_patterns)
            if dynamic_links:
                # 分类链接
                from urllib.parse import urlparse
                base_domain = urlparse(url).netloc
                same_domain = []
                external_domain = []
                
                for link in dynamic_links:
                    parsed = urlparse(link)
                    if parsed.netloc == base_domain:
                        same_domain.append(link)
                    else:
                        external_domain.append(link)
                
                result_text = f"🔗 从 {url} 提取到 {len(dynamic_links)} 个有效链接：\n\n"
                
                if same_domain:
                    result_text += f"📂 站内链接 ({len(same_domain)} 个)：\n"
                    for i, link in enumerate(same_domain[:15], 1):
                        result_text += f"  {i}. {link}\n"
                    if len(same_domain) > 15:
                        result_text += f"  ... 还有 {len(same_domain) - 15} 个\n"
                    result_text += "\n"
                
                if external_domain:
                    result_text += f"🌐 外部链接 ({len(external_domain)} 个)：\n"
                    for i, link in enumerate(external_domain[:10], 1):
                        result_text += f"  {i}. {link}\n"
                    if len(external_domain) > 10:
                        result_text += f"  ... 还有 {len(external_domain) - 10} 个\n"
                
                return result_text
        
        try:
            req = urllib.request.Request(url, headers=self._get_headers())
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=60, context=self._create_ssl_context())
            )
            
            html = response.read().decode('utf-8', errors='ignore')
            
            # 提取所有链接
            from urllib.parse import urljoin, urlparse
            
            all_links = []
            link_pattern = r'href=["\']([^"\']+)["\']'
            matches = re.findall(link_pattern, html, re.IGNORECASE)
            
            base_domain = urlparse(url).netloc
            
            for match in matches:
                match = match.strip()
                
                # 跳过无效模式
                if any(re.match(p, match, re.IGNORECASE) for p in invalid_patterns):
                    continue
                
                # 补全相对路径
                if not match.startswith('http'):
                    match = urljoin(url, match)
                
                # 解析URL
                try:
                    parsed = urlparse(match)
                except:
                    continue
                
                # 跳过无效后缀
                path_lower = parsed.path.lower()
                if any(path_lower.endswith(ext) for ext in invalid_extensions):
                    continue
                
                # 跳过广告链接
                url_lower = match.lower()
                if any(kw in url_lower for kw in ad_keywords):
                    continue
                
                # 跳过相同域名的基础页面
                if parsed.netloc == base_domain and parsed.path in ['/', '', '/index.html', '/index.php']:
                    continue
                
                # 跳过查询参数过多的链接
                if len(parsed.query) > 200:
                    continue
                
                all_links.append(match)
            
            # 去重
            unique_links = list(dict.fromkeys(all_links))
            
            # 分类链接
            same_domain = []
            external_domain = []
            
            for link in unique_links:
                parsed = urlparse(link)
                if parsed.netloc == base_domain:
                    same_domain.append(link)
                else:
                    external_domain.append(link)
            
            if not unique_links:
                return f"❌ 未在 {url} 中找到有效链接"
            
            # 格式化输出
            result_text = f"🔗 从 {url} 提取到 {len(unique_links)} 个有效链接：\n\n"
            
            if same_domain:
                result_text += f"📂 站内链接 ({len(same_domain)} 个)：\n"
                for i, link in enumerate(same_domain[:15], 1):
                    result_text += f"  {i}. {link}\n"
                if len(same_domain) > 15:
                    result_text += f"  ... 还有 {len(same_domain) - 15} 个\n"
                result_text += "\n"
            
            if external_domain:
                result_text += f"🌐 外部链接 ({len(external_domain)} 个)：\n"
                for i, link in enumerate(external_domain[:10], 1):
                    result_text += f"  {i}. {link}\n"
                if len(external_domain) > 10:
                    result_text += f"  ... 还有 {len(external_domain) - 10} 个\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"提取页面链接失败: {e}")
            return f"❌ 提取页面链接失败: {str(e)}"
    
    async def _handle_general(self, params: Dict) -> str:
        """处理通用请求"""
        # 获取原始文本，支持多种参数名
        original_text = params.get("original_text", "") or params.get("text", "") or params.get("query", "") or params.get("keyword", "")
        
        if not original_text:
            return "❌ 请提供搜索关键词或操作指令"
        
        # 更新 params，确保后续方法可以获取到 query
        if "query" not in params and "keyword" not in params:
            params["query"] = original_text
        
        if "页面链接" in original_text or "提取链接" in original_text:
            return await self._extract_page_links(params)
        elif "视频链接" in original_text or "mp4链接" in original_text.lower():
            return await self._scrape_links(params)
        elif "搜索" in original_text:
            return await self._web_search(params)
        elif "抓取" in original_text or "爬取" in original_text:
            return await self._crawl_webpage(params)
        else:
            # 默认进行网络搜索
            return await self._web_search(params)
    
    async def _web_search(self, params: Dict) -> str:
        """网络搜索"""
        query = params.get("query", "") or params.get("keyword", "")
        
        if not query:
            return "❌ 请提供搜索关键词"
        
        original_query = query
        
        try:
            from ...config import settings
            user_address = settings.user.address or ""
            user_city = settings.user.city or ""
            
            if user_address and user_city and user_city not in user_address:
                full_address = f"{user_city}{user_address}"
            else:
                full_address = user_address or user_city
            
            if full_address:
                location_keywords = ["周边", "附近", "周围", "就近", "哪里有", "哪有"]
                has_location_keyword = any(kw in query for kw in location_keywords)
                
                if has_location_keyword:
                    for kw in location_keywords:
                        query = query.replace(kw, f"{full_address}")
                    logger.info(f"🔍 替换位置关键词: {original_query} -> {query}")
        except Exception as e:
            logger.warning(f"处理位置信息失败: {e}")
        
        self._send_message_to_chat(f"🔍 正在搜索...\n\n📝 关键词: {query}")
        
        logger.info(f"🔍 网络搜索: {query}")
        
        results = []
        
        try:
            baidu_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}"
            baidu_result = await self._fetch_search_results(baidu_url, "百度")
            if baidu_result:
                results.extend(baidu_result)
        except Exception as e:
            logger.warning(f"百度搜索失败: {e}")
        
        if not results:
            try:
                bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
                bing_result = await self._fetch_search_results(bing_url, "必应")
                if bing_result:
                    results.extend(bing_result)
            except Exception as e:
                logger.warning(f"必应搜索失败: {e}")
        
        if results:
            raw_results = []
            seen = set()
            for title, snippet, url in results[:10]:
                if title in seen:
                    continue
                seen.add(title)
                raw_results.append(f"标题: {title}\n摘要: {snippet}\n链接: {url}")
            
            raw_text = "\n\n".join(raw_results)
            
            try:
                llm_response = await self._summarize_search_results(query, raw_text)
                if llm_response:
                    logger.info(f"✅ LLM 总结成功，长度: {len(llm_response)}")
                    return llm_response
            except Exception as e:
                logger.warning(f"LLM 总结失败: {e}")
            
            result_text = f"🔍 搜索结果: {query}\n\n"
            seen = set()
            for i, (title, snippet, url) in enumerate(results[:8], 1):
                if title in seen:
                    continue
                seen.add(title)
                result_text += f"**{i}. {title}**\n"
                if snippet:
                    result_text += f"   {snippet}\n"
                result_text += f"   🔗 {url}\n\n"
            
            result_text += "💡 点击链接可查看详情"
            return result_text
        else:
            search_engines = [
                ("百度", f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}"),
                ("必应", f"https://www.bing.com/search?q={urllib.parse.quote(query)}"),
            ]
            result_text = f"🔍 搜索: {query}\n\n未能获取搜索结果，请尝试以下链接：\n\n"
            for name, url in search_engines:
                result_text += f"• {name}: {url}\n"
            return result_text
    
    async def _summarize_search_results(self, query: str, raw_results: str) -> Optional[str]:
        """使用 LLM 总结搜索结果"""
        try:
            from ...llm import LLMGateway
            from ...config import settings
            
            llm = LLMGateway(settings.llm)
            
            user_address = settings.user.address or ""
            user_city = settings.user.city or ""
            
            # 检查搜索关键词中是否包含城市名
            # 如果用户明确指定了城市（如"深圳"、"北京"），则不使用用户默认位置
            common_cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安", "南京", "天津", "苏州", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明"]
            has_explicit_city = any(city in query for city in common_cities)
            
            if has_explicit_city:
                # 用户明确指定了城市，不使用默认位置
                location_info = ""
                logger.info(f"📍 用户明确指定了城市，不使用默认位置")
            else:
                # 用户没有指定城市，使用默认位置
                if user_address and user_city and user_city not in user_address:
                    full_address = f"{user_city}{user_address}"
                else:
                    full_address = user_address or user_city or "未知位置"
                location_info = f"\n用户位置: {full_address}"
                logger.info(f"📍 使用用户默认位置: {full_address}")
            
            prompt = f"""你是一个智能助手，请根据以下搜索结果，为用户整理出有用的信息。{location_info}
用户搜索: {query}

搜索结果:
{raw_results}

请按要求整理:
1. 提取最相关、最有价值的信息
2. 如果是找店铺/餐厅，列出名称、地址、特色、人均消费等信息
3. 如果是找景点，列出名称、位置、特色、门票等信息
4. 如果是其他信息，整理成清晰易读的格式
5. 去除重复和无关信息
6. 用简洁自然的语言回答，不要直接复制搜索结果
7. 如果搜索结果中没有找到相关信息，请明确告知用户

重要：
- 不要添加"需要我帮您..."之类的后续服务建议
- 不要提到导航链接、地图标记、设置提醒等功能
- 只输出搜索结果的整理内容，不要加开场白和结束语"""

            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            if response and response.content:
                return response.content
            
        except Exception as e:
            logger.error(f"LLM 总结搜索结果失败: {e}")
        
        return None

    async def _fetch_search_results(self, url: str, engine: str) -> List[tuple]:
        """抓取搜索结果页面"""
        results = []
        
        try:
            if PLAYWRIGHT_AVAILABLE:
                logger.info(f"🌐 使用 Playwright 抓取: {url}")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=15000)
                        await page.wait_for_timeout(2000)
                        
                        content = await page.content()
                        logger.info(f"📄 获取到页面内容，长度: {len(content)}")
                        
                        if 'baidu' in url:
                            results = self._parse_baidu_results(content)
                        elif 'bing' in url:
                            results = self._parse_bing_results(content)
                        
                        logger.info(f"✅ 解析到 {len(results)} 条结果")
                            
                    finally:
                        await browser.close()
            else:
                logger.info(f"🌐 使用 aiohttp 抓取: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                }
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=15) as response:
                        content = await response.text()
                        logger.info(f"📄 获取到页面内容，长度: {len(content)}")
                        
                        if 'baidu' in url:
                            results = self._parse_baidu_results(content)
                        elif 'bing' in url:
                            results = self._parse_bing_results(content)
                        
                        logger.info(f"✅ 解析到 {len(results)} 条结果")
                            
        except Exception as e:
            logger.error(f"抓取搜索结果失败 ({engine}): {e}")
        
        return results
    
    def _parse_baidu_results(self, html: str) -> List[tuple]:
        """解析百度搜索结果"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            selectors = [
                '.result',
                '.c-container',
                '#content_left .result',
                '.c-group-content',
                'div[class*="result"]',
            ]
            
            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found:
                    items = found
                    logger.info(f"📊 百度选择器 '{selector}' 找到 {len(found)} 个元素")
                    break
            
            if not items:
                items = soup.find_all('div', class_=lambda x: x and ('result' in x or 'container' in x))
                logger.info(f"📊 百度通过 class 匹配找到 {len(items)} 个元素")
            
            for item in items:
                try:
                    title_elem = item.select_one('h3, .t, .c-title, a[href] em, .c-title-en')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    snippet_elem = item.select_one('.c-abstract, .c-span9, .c-color-text, p[class*="content"]')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    link_elem = item.select_one('a[href]')
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    if title and link and 'baidu.com' not in title:
                        if link.startswith('/'):
                            link = 'https://www.baidu.com' + link
                        results.append((title, snippet[:200] if snippet else '', link))
                        
                except Exception as e:
                    continue
                    
        except ImportError:
            logger.warning("BeautifulSoup 未安装，使用正则解析")
            import re
            title_pattern = r'<h3[^>]*>(.*?)</h3>'
            titles = re.findall(title_pattern, html, re.DOTALL)
            
            for title in titles[:10]:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if clean_title:
                    results.append((clean_title, '', ''))
        
        except Exception as e:
            logger.error(f"解析百度结果失败: {e}")
                    
        return results
    
    def _parse_bing_results(self, html: str) -> List[tuple]:
        """解析必应搜索结果"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            selectors = [
                '.b_algo',
                '#b_results .b_algo',
                'li.b_algo',
            ]
            
            items = []
            for selector in selectors:
                found = soup.select(selector)
                if found:
                    items = found
                    logger.info(f"📊 必应选择器 '{selector}' 找到 {len(found)} 个元素")
                    break
            
            for item in items:
                try:
                    title_elem = item.select_one('h2, .b_topTitle, a[href]')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    snippet_elem = item.select_one('.b_caption p, .b_paractl, p')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    link_elem = item.select_one('a[href]')
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    if title and link:
                        results.append((title, snippet[:200] if snippet else '', link))
                        
                except Exception as e:
                    continue
                    
        except ImportError:
            logger.warning("BeautifulSoup 未安装，使用正则解析")
            import re
            title_pattern = r'<h2[^>]*>(.*?)</h2>'
            titles = re.findall(title_pattern, html, re.DOTALL)
            
            for title in titles[:10]:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if clean_title:
                    results.append((clean_title, '', ''))
        
        except Exception as e:
            logger.error(f"解析必应结果失败: {e}")
            
        return results
    
    async def _scrape_links(self, params: Dict) -> str:
        """抓取网页中的链接"""
        url = params.get("url", "")
        link_type = params.get("link_type", "")  # video, image, all
        is_workflow = params.get("is_workflow", False)
        
        # 从 action 参数推断链接类型
        action = params.get("action", "")
        if "m3u8" in action.lower() and not link_type:
            link_type = "m3u8"
        elif "mp4" in action.lower() and not link_type:
            link_type = "mp4"
        
        if not url:
            return "❌ 请提供网页 URL"
        
        # 清理 URL - 移除反引号、逗号等
        url = url.strip().strip('`').strip(',').strip()
        
        # 发送提示消息
        type_desc = "链接" if not link_type else f"{link_type}链接"
        self._send_message_to_chat(f"🕷️ 正在抓取网页{type_desc}...\n\n🔗 URL: {url[:80]}{'...' if len(url) > 80 else ''}")
        
        logger.info(f"🔗 抓取链接: {url}, 类型: {link_type}, 工作流: {is_workflow}")
        
        # 对于视频链接抓取，优先使用 Playwright 动态抓取
        if PLAYWRIGHT_AVAILABLE and ("视频" in str(params) or "mp4" in str(params).lower() or "m3u8" in str(params).lower() or link_type in ["mp4", "m3u8"]):
            logger.info(f"🎬 使用 Playwright 动态抓取视频链接...")
            dynamic_links, error = await self._scrape_dynamic_video(url)
            if dynamic_links:
                # 根据任务类型过滤链接
                filtered_links = dynamic_links
                filter_type = "视频"
                if "mp4" in link_type.lower() or "mp4" in str(params).lower():
                    filtered_links = [l for l in dynamic_links if '.mp4' in l.lower()]
                    filter_type = "MP4视频"
                elif "m3u8" in link_type.lower() or "m3u8" in str(params).lower():
                    filtered_links = [l for l in dynamic_links if '.m3u8' in l.lower()]
                    filter_type = "M3U8流媒体"
                
                if filtered_links:
                    # 如果是工作流模式，只返回第一个链接
                    if is_workflow:
                        logger.info(f"🔄 工作流模式: 返回第一个视频链接")
                        return filtered_links[0]
                    
                    result_text = f"🎬 从 {url} 提取到 {len(filtered_links)} 个{filter_type}链接：\n\n"
                    for i, link in enumerate(filtered_links[:20], 1):
                        result_text += f"{i}. {link}\n"
                    return result_text
        
        try:
            req = urllib.request.Request(url, headers=self._get_headers())
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=60, context=self._create_ssl_context())
            )
            
            html = response.read().decode('utf-8', errors='ignore')
            
            # 提取链接
            links = []
            
            # 视频链接模式 - 扩展更多格式和属性
            video_patterns = [
                r'href=["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'src=["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'data-src=["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'data-url=["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'data-video=["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'url:\s*["\']([^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*)["\']',
                r'https?://[^\s<>"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)',
                r'["\']https?://[^"\']+\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m3u8|m3u|ts)[^"\']*["\']',
            ]
            
            # 流媒体和API链接模式
            stream_patterns = [
                r'["\']https?://[^"\']*\.m3u8[^"\']*["\']',
                r'["\']https?://[^"\']*\.ts[^"\']*["\']',
                r'["\']https?://[^"\']*/video/[^"\']*["\']',
                r'["\']https?://[^"\']*/play/[^"\']*["\']',
                r'["\']https?://[^"\']*/stream/[^"\']*["\']',
                r'["\']https?://[^"\']*/api/[^"\']*video[^"\']*["\']',
                r'videoUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'video_url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'playUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'play_url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'source["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            ]
            
            # 图片链接模式
            image_patterns = [
                r'src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|bmp)[^"\']*)["\']',
                r'href=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|bmp)[^"\']*)["\']',
                r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|bmp)[^"\']*)["\']',
            ]
            
            # 所有链接模式
            all_patterns = [
                r'href=["\']([^"\']+)["\']',
                r'src=["\']([^"\']+)["\']',
            ]
            
            if link_type == "video" or "视频" in str(params):
                patterns = video_patterns + stream_patterns
                type_name = "视频"
            elif link_type == "image" or "图片" in str(params):
                patterns = image_patterns
                type_name = "图片"
            else:
                patterns = video_patterns + stream_patterns + all_patterns
                type_name = "视频"
            
            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                    if match:
                        # 清理引号
                        match = match.strip('"\'')
                        if match and match not in links:
                            # 过滤掉无效链接
                            if match.startswith('http') or match.startswith('/'):
                                if not match.startswith('http'):
                                    # 补全相对路径
                                    from urllib.parse import urljoin
                                    match = urljoin(url, match)
                                # 过滤掉一些明显不是视频的链接
                                if not any(x in match.lower() for x in ['.css', '.js', '.json', '.woff', '.ttf', '.ico']):
                                    links.append(match)
            
            if not links:
                # 如果静态抓取失败，尝试使用 Playwright 动态抓取
                if PLAYWRIGHT_AVAILABLE:
                    logger.info(f"静态抓取未找到链接，尝试 Playwright 动态抓取...")
                    dynamic_links, error = await self._scrape_dynamic_video(url)
                    if dynamic_links:
                        # 根据任务类型过滤链接
                        filtered_links = dynamic_links
                        filter_type = type_name
                        if "mp4" in link_type.lower() or "mp4" in str(params).lower():
                            filtered_links = [l for l in dynamic_links if '.mp4' in l.lower()]
                            filter_type = "MP4视频"
                        elif "m3u8" in link_type.lower() or "m3u8" in str(params).lower():
                            filtered_links = [l for l in dynamic_links if '.m3u8' in l.lower()]
                            filter_type = "M3U8流媒体"
                        
                        if filtered_links:
                            result_text = f"🎬 从 {url} 提取到 {len(filtered_links)} 个{filter_type}链接（动态抓取）：\n\n"
                            for i, link in enumerate(filtered_links[:20], 1):
                                result_text += f"{i}. {link}\n"
                            return result_text
                
                # 如果动态抓取也失败，返回页面中的所有URL供参考
                all_urls = re.findall(r'https?://[^\s<>"\']+', html)
                all_urls = [u.strip('"\'') for u in all_urls if not any(x in u.lower() for x in ['.css', '.js', '.json', '.woff', '.ttf', '.ico', '.png', '.jpg', '.gif'])]
                unique_urls = list(dict.fromkeys(all_urls))[:10]
                
                if unique_urls:
                    result_text = f"⚠️ 未找到直接的视频链接，但发现以下URL可能包含视频资源：\n\n"
                    for i, link in enumerate(unique_urls, 1):
                        result_text += f"{i}. {link}\n"
                    result_text += f"\n💡 提示：该网站可能使用JavaScript动态加载视频，建议在浏览器中查看网络请求获取真实视频地址。"
                    return result_text
                else:
                    return f"❌ 未在 {url} 中找到视频链接\n\n💡 提示：该网站可能使用JavaScript动态加载视频内容，建议使用浏览器开发者工具查看网络请求。"
            
            # 去重并限制数量
            unique_links = list(dict.fromkeys(links))[:20]
            
            # 根据任务类型过滤链接
            if "mp4" in link_type.lower() or "mp4" in str(params).lower():
                unique_links = [l for l in unique_links if '.mp4' in l.lower()]
                type_name = "MP4视频"
            elif "m3u8" in link_type.lower() or "m3u8" in str(params).lower():
                unique_links = [l for l in unique_links if '.m3u8' in l.lower()]
                type_name = "M3U8流媒体"
            
            if not unique_links:
                return f"❌ 未在 {url} 中找到{type_name}链接"
            
            # 如果是工作流模式，只返回第一个链接
            if is_workflow and unique_links:
                logger.info(f"🔄 工作流模式: 返回第一个视频链接")
                return unique_links[0]
            
            result_text = f"🔗 从 {url} 提取到 {len(unique_links)} 个{type_name}链接：\n\n"
            for i, link in enumerate(unique_links, 1):
                result_text += f"{i}. {link}\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"静态抓取链接失败: {e}")
            
            # 静态抓取失败时，尝试 Playwright 动态抓取
            if PLAYWRIGHT_AVAILABLE:
                logger.info(f"静态抓取超时，尝试 Playwright 动态抓取...")
                try:
                    dynamic_links, error = await self._scrape_dynamic_video(url)
                    if dynamic_links:
                        # 根据任务类型过滤链接
                        filtered_links = dynamic_links
                        filter_type = "视频"
                        if "mp4" in link_type.lower() or "mp4" in str(params).lower():
                            filtered_links = [l for l in dynamic_links if '.mp4' in l.lower()]
                            filter_type = "MP4视频"
                        elif "m3u8" in link_type.lower() or "m3u8" in str(params).lower():
                            filtered_links = [l for l in dynamic_links if '.m3u8' in l.lower()]
                            filter_type = "M3U8流媒体"
                        
                        if filtered_links:
                            # 如果是工作流模式，只返回第一个链接
                            if is_workflow:
                                logger.info(f"🔄 工作流模式: 返回第一个视频链接")
                                return filtered_links[0]
                            
                            result_text = f"🎬 从 {url} 提取到 {len(filtered_links)} 个{filter_type}链接（动态抓取）：\n\n"
                            for i, link in enumerate(filtered_links[:20], 1):
                                result_text += f"{i}. {link}\n"
                            return result_text
                except Exception as e2:
                    logger.error(f"动态抓取也失败: {e2}")
            
            return f"❌ 抓取链接失败: {str(e)}"
    
    async def _scrape_dynamic_video(self, url: str) -> Tuple[List[str], str]:
        """使用 Playwright 抓取动态加载的视频链接"""
        if not PLAYWRIGHT_AVAILABLE:
            return [], "Playwright 未安装，无法抓取动态内容"
        
        video_links = []
        m3u8_links = []
        ts_links = []
        error_msg = ""
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # 监听网络请求
                async def handle_response(response):
                    url_str = response.url
                    # 检查是否是视频相关请求
                    if '.m3u8' in url_str.lower():
                        logger.info(f"🎬 发现 m3u8 请求: {url_str[:100]}...")
                        m3u8_links.append(url_str)
                    elif '.ts' in url_str.lower() and '.m3u8' not in url_str.lower():
                        logger.info(f"🎬 发现 TS 分片: {url_str[:80]}...")
                        ts_links.append(url_str)
                    elif any(ext in url_str.lower() for ext in ['.mp4', '.flv', '.webm', '.mkv', '.avi']):
                        logger.info(f"🎬 发现视频请求: {url_str[:100]}...")
                        video_links.append(url_str)
                    # 检查是否是视频API请求
                    elif any(keyword in url_str.lower() for keyword in ['/video/', '/play/', '/stream/', 'playurl', 'videourl', 'video_url', 'getvideo']):
                        if not any(ext in url_str.lower() for ext in ['.css', '.js', '.png', '.jpg', '.gif', '.ico', '.woff', '.ttf']):
                            logger.info(f"🎬 发现视频API请求: {url_str}")
                            video_links.append(url_str)
                
                page.on("response", handle_response)
                
                # 访问页面
                logger.info(f"🎭 Playwright 正在访问: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 等待页面加载
                await page.wait_for_timeout(3000)
                
                # 尝试点击播放按钮
                play_selectors = [
                    'button[class*="play"]',
                    '.play-button',
                    '.vjs-big-play-button',
                    '[class*="play-btn"]',
                    'video',
                    '.player',
                    '[class*="player"]',
                ]
                for selector in play_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click(timeout=2000)
                            logger.info(f"🎭 点击了播放按钮: {selector}")
                            break
                    except:
                        pass
                
                # 等待视频开始播放，捕获更多 TS 分片
                logger.info("🎭 等待视频播放，捕获分片...")
                await page.wait_for_timeout(5000)
                
                # 尝试拖动进度条到不同位置，触发加载更多分片
                try:
                    video = await page.query_selector('video')
                    if video:
                        # 获取视频时长
                        duration = await video.evaluate('el => el.duration || 0')
                        logger.info(f"🎭 视频时长: {duration:.1f} 秒")
                        
                        # 跳转到不同位置触发加载
                        positions = [0.1, 0.3, 0.5, 0.7, 0.9]
                        for pos in positions:
                            try:
                                await video.evaluate(f'el => el.currentTime = el.duration * {pos}')
                                await page.wait_for_timeout(2000)
                            except:
                                pass
                except Exception as e:
                    logger.warning(f"拖动进度条失败: {e}")
                
                # 滚动页面触发懒加载
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(3000)
                
                # 尝试执行 JavaScript 获取播放器配置
                try:
                    player_info = await page.evaluate('''() => {
                        const result = {};
                        // 尝试获取播放器实例
                        if (window.__playinfo__) result.playinfo = window.__playinfo__;
                        if (window.player) result.player = window.player;
                        // 尝试获取 video 元素信息
                        const videos = document.querySelectorAll('video');
                        if (videos.length > 0) {
                            result.videoSrc = videos[0].src;
                            result.videoCurrentSrc = videos[0].currentSrc;
                        }
                        return result;
                    }''')
                    if player_info:
                        logger.info(f"🎭 播放器信息: {str(player_info)[:200]}")
                        # 从播放器信息中提取链接
                        if player_info.get('videoSrc'):
                            video_links.append(player_info['videoSrc'])
                        if player_info.get('videoCurrentSrc'):
                            video_links.append(player_info['videoCurrentSrc'])
                except Exception as e:
                    logger.warning(f"获取播放器信息失败: {e}")
                
                # 如果还没有捕获到足够的分片，继续等待
                if len(ts_links) < 20 and not m3u8_links:
                    logger.info("🎭 继续等待捕获更多分片...")
                    await page.wait_for_timeout(10000)
                
                # 从页面源码中提取
                content = await page.content()
                
                # 提取 m3u8 链接
                m3u8_pattern = r'https?://[^\s<>"\']+[^\s<>"\']*\.m3u8[^\s<>"\']*'
                m3u8_matches = re.findall(m3u8_pattern, content, re.IGNORECASE)
                for m in m3u8_matches:
                    if m not in m3u8_links:
                        m3u8_links.append(m)
                
                # 提取 mp4 链接
                mp4_pattern = r'https?://[^\s<>"\']+[^\s<>"\']*\.mp4[^\s<>"\']*'
                mp4_matches = re.findall(mp4_pattern, content, re.IGNORECASE)
                for m in mp4_matches:
                    if m not in video_links:
                        video_links.append(m)
                
                # 提取 JSON 中的视频链接
                json_patterns = [
                    r'"url"\s*:\s*"([^"]+\.(?:mp4|m3u8)[^"]*)"',
                    r'"src"\s*:\s*"([^"]+\.(?:mp4|m3u8)[^"]*)"',
                    r'"source"\s*:\s*"([^"]+\.(?:mp4|m3u8)[^"]*)"',
                    r'"videoUrl"\s*:\s*"([^"]+)"',
                    r'"playUrl"\s*:\s*"([^"]+)"',
                ]
                for pattern in json_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for m in matches:
                        if m.startswith('http'):
                            if '.m3u8' in m.lower():
                                if m not in m3u8_links:
                                    m3u8_links.append(m)
                            elif m not in video_links:
                                video_links.append(m)
                
                await browser.close()
                
                logger.info(f"🎭 Playwright 抓取完成: m3u8={len(m3u8_links)}, ts={len(ts_links)}, video={len(video_links)}")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Playwright 抓取失败: {e}")
        
        # 如果没有捕获到 m3u8，尝试从 TS 分片 URL 推断 m3u8 地址
        if not m3u8_links and ts_links:
            for ts_url in ts_links[:3]:
                # 腾讯视频 TS URL 格式: https://xxx.gtimg.com/KEY/xxx
                # 尝试提取基础路径
                m3u8_match = re.search(r'(https?://[^/]+/[A-Za-z0-9_-]+/)', ts_url)
                if m3u8_match:
                    base_url = m3u8_match.group(1)
                    # 尝试多种可能的 m3u8 路径
                    potential_m3u8_list = [
                        base_url + 'index.m3u8',
                        base_url + 'playlist.m3u8',
                        base_url.rstrip('/') + '.m3u8',
                    ]
                    for potential_m3u8 in potential_m3u8_list:
                        logger.info(f"🎭 尝试推断的 m3u8 地址: {potential_m3u8}")
                        m3u8_links.append(potential_m3u8)
                    break
        
        # 合并并去重，优先 m3u8 > ts > video
        all_links = list(dict.fromkeys(m3u8_links + ts_links + video_links))
        return all_links, error_msg
    
    async def _extract_links_with_playwright(self, url: str, ad_keywords: list, invalid_extensions: list, invalid_patterns: list) -> List[str]:
        """使用 Playwright 提取页面链接"""
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        all_links = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # 监听网络请求
                async def handle_response(response):
                    url_str = response.url
                    # 过滤广告和无效链接
                    url_lower = url_str.lower()
                    if any(kw in url_lower for kw in ad_keywords):
                        return
                    if any(url_str.lower().endswith(ext) for ext in invalid_extensions):
                        return
                    all_links.append(url_str)
                
                page.on("response", handle_response)
                
                # 访问页面
                logger.info(f"🎭 Playwright 正在访问: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 等待页面加载
                await page.wait_for_timeout(3000)
                
                # 滚动页面触发懒加载
                for i in range(3):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(1000)
                
                # 从页面源码中提取链接
                content = await page.content()
                
                from urllib.parse import urljoin, urlparse
                base_domain = urlparse(url).netloc
                
                # 提取 href 链接
                href_pattern = r'href=["\']([^"\']+)["\']'
                href_matches = re.findall(href_pattern, content, re.IGNORECASE)
                
                for match in href_matches:
                    match = match.strip()
                    
                    # 跳过无效模式
                    if any(re.match(p, match, re.IGNORECASE) for p in invalid_patterns):
                        continue
                    
                    # 补全相对路径
                    if not match.startswith('http'):
                        match = urljoin(url, match)
                    
                    # 过滤广告和无效链接
                    url_lower = match.lower()
                    if any(kw in url_lower for kw in ad_keywords):
                        continue
                    
                    try:
                        parsed = urlparse(match)
                        path_lower = parsed.path.lower()
                        if any(path_lower.endswith(ext) for ext in invalid_extensions):
                            continue
                    except:
                        continue
                    
                    all_links.append(match)
                
                await browser.close()
                
                logger.info(f"🎭 Playwright 提取链接完成: {len(all_links)} 个")
                
        except Exception as e:
            logger.error(f"Playwright 提取链接失败: {e}")
        
        # 去重
        return list(dict.fromkeys(all_links))
    
    async def _scrape_links_with_playwright(self, params: Dict) -> str:
        """使用 Playwright 抓取动态页面的视频链接"""
        url = params.get("url", "")
        
        if not url:
            return "❌ 请提供网页 URL"
        
        if not PLAYWRIGHT_AVAILABLE:
            return "❌ Playwright 未安装，无法抓取动态页面。\n\n请运行以下命令安装：\npip install playwright\nplaywright install chromium"
        
        logger.info(f"🎭 使用 Playwright 抓取动态页面: {url}")
        
        video_links, error = await self._scrape_dynamic_video(url)
        
        if video_links:
            result_text = f"🎬 从 {url} 提取到 {len(video_links)} 个视频链接：\n\n"
            for i, link in enumerate(video_links[:20], 1):
                result_text += f"{i}. {link}\n"
            return result_text
        else:
            return f"❌ 未找到视频链接。\n\n错误信息: {error}\n\n💡 提示：该网站可能有防爬机制或需要登录。"

    async def _search_mp3(self, params: Dict) -> str:
        """
        搜索 MP3 音乐链接
        使用国内可用的音乐源并解析真实 MP3 链接
        """
        keyword = params.get("keyword", "")
        artist = params.get("artist", "")

        if not keyword:
            return "❌ 请提供搜索关键词"

        search_query = f"{artist} {keyword}" if artist else keyword
        logger.info(f"🎵 搜索 MP3: {search_query}")

        # 创建任务
        task_id = f"mp3_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        crawl_task = CrawlTask(
            task_id=task_id,
            keyword=search_query,
            task_type="mp3"
        )
        self.tasks[task_id] = crawl_task
        self.active_tasks.add(task_id)

        try:
            crawl_task.status = "running"

            # 使用多个解析源获取真实 MP3 链接
            all_results = []

            # 1. 使用第三方解析 API（优先）
            api_results = await self._search_from_music_api(search_query)
            all_results.extend(api_results)

            # 2. 使用网页抓取解析
            if len(all_results) < 3:
                web_results = await self._search_from_music_websites(search_query)
                all_results.extend(web_results)

            # 去重并排序
            seen_urls = set()
            unique_results = []
            for r in all_results:
                if r.url not in seen_urls and r.url.endswith(('.mp3', '.m4a', '.flac')):
                    seen_urls.add(r.url)
                    unique_results.append(r)

            crawl_task.results = unique_results[:10]  # 最多保留10个结果
            crawl_task.status = "completed"
            crawl_task.completed_at = datetime.now()

            # 格式化结果
            if crawl_task.results:
                result_text = f"🎵 找到 {len(crawl_task.results)} 个 MP3 资源:\n\n"
                for i, result in enumerate(crawl_task.results[:5], 1):
                    result_text += f"{i}. {result.title}\n"
                    result_text += f"   链接: {result.url[:80]}...\n"
                    result_text += f"   来源: {result.source}\n"
                    if result.quality != "unknown":
                        result_text += f"   音质: {result.quality}\n"
                    result_text += "\n"

                # 保存到文件
                await self._save_results_to_file(task_id, crawl_task.results)
                result_text += f"📁 完整结果已保存到: data/crawler/{task_id}.json"
            else:
                result_text = f"❌ 未找到 MP3 资源: {search_query}\n\n建议:\n1. 尝试使用英文关键词\n2. 检查歌曲名是否正确\n3. 尝试添加歌手名"

            self.active_tasks.discard(task_id)
            return result_text

        except Exception as e:
            crawl_task.status = "failed"
            crawl_task.error_message = str(e)
            crawl_task.completed_at = datetime.now()
            self.active_tasks.discard(task_id)
            logger.error(f"MP3 搜索失败: {e}")
            return f"❌ MP3 搜索失败: {str(e)}"

    async def _search_from_music_api(self, keyword: str) -> List[SearchResult]:
        """使用音乐 API 搜索真实 MP3 链接"""
        results = []

        # 使用多个免费音乐 API
        api_tasks = [
            self._api_liumingye(keyword),
            self._api_wyymusic(keyword),
            self._api_kuwo(keyword),
        ]

        api_results = await asyncio.gather(*api_tasks, return_exceptions=True)

        for result in api_results:
            if isinstance(result, list):
                results.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"API 搜索失败: {result}")

        return results

    async def _api_liumingye(self, keyword: str) -> List[SearchResult]:
        """使用 liumingye.cn API 搜索"""
        results = []
        try:
            # 这个 API 提供真实的 MP3 链接
            search_url = f"https://api.liumingye.cn/m/api/search?keyword={urllib.parse.quote(keyword)}&page=1"

            headers = self._get_headers("https://www.liumingye.cn")
            headers['Accept'] = 'application/json'

            req = urllib.request.Request(search_url, headers=headers)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=15, context=self._create_ssl_context())
            )

            data = json.loads(response.read().decode('utf-8'))

            if data.get('code') == 200 and data.get('data', {}).get('list'):
                for item in data['data']['list'][:5]:
                    song_id = item.get('id')
                    if song_id:
                        # 获取播放链接
                        play_url = f"https://api.liumingye.cn/m/api/link?id={song_id}"
                        play_req = urllib.request.Request(play_url, headers=headers)
                        play_response = await loop.run_in_executor(
                            None,
                            lambda: urllib.request.urlopen(play_req, timeout=15, context=self._create_ssl_context())
                        )
                        play_data = json.loads(play_response.read().decode('utf-8'))

                        if play_data.get('code') == 200 and play_data.get('data'):
                            mp3_url = play_data['data'].get('url')
                            if mp3_url:
                                results.append(SearchResult(
                                    title=f"{item.get('name', 'Unknown')} - {item.get('artist', 'Unknown')}",
                                    url=mp3_url,
                                    source="liumingye.cn",
                                    quality=item.get('quality', '128kbps'),
                                    extra_info={
                                        "song_id": song_id,
                                        "album": item.get('album', ''),
                                        "duration": item.get('duration', 0)
                                    }
                                ))

            logger.info(f"liumingye.cn 找到 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.warning(f"liumingye.cn API 失败: {e}")
            return []

    async def _api_wyymusic(self, keyword: str) -> List[SearchResult]:
        """使用网易云音乐 API 搜索"""
        results = []
        try:
            # 使用多个可用的网易云 API
            apis = [
                ("https://api.injahow.cn/meting/?type=search&id=netease&", "search", "title"),
                ("https://music.api.lolimi.cn/?type=search&id=netease&", "search", "title"),
            ]

            headers = self._get_headers()
            headers['Accept'] = 'application/json'

            loop = asyncio.get_event_loop()

            for api_base, search_param, title_field in apis:
                try:
                    search_url = f"{api_base}{search_param}={urllib.parse.quote(keyword)}"

                    req = urllib.request.Request(search_url, headers=headers)
                    response = await loop.run_in_executor(
                        None,
                        lambda: urllib.request.urlopen(req, timeout=10, context=self._create_ssl_context())
                    )

                    data = json.loads(response.read().decode('utf-8', errors='ignore'))

                    if isinstance(data, list) and len(data) > 0:
                        for song in data[:5]:
                            song_id = song.get('song_id') or song.get('id')
                            if song_id:
                                # 获取播放链接
                                url_endpoint = f"{api_base}type=url&id={song_id}"
                                url_req = urllib.request.Request(url_endpoint, headers=headers)
                                url_response = await loop.run_in_executor(
                                    None,
                                    lambda: urllib.request.urlopen(url_req, timeout=10, context=self._create_ssl_context())
                                )
                                url_data = json.loads(url_response.read().decode('utf-8', errors='ignore'))

                                mp3_url = url_data.get('url') if isinstance(url_data, dict) else None
                                if mp3_url:
                                    results.append(SearchResult(
                                        title=f"{song.get('name', song.get('title', 'Unknown'))} - {song.get('artist', song.get('author', 'Unknown'))}",
                                        url=mp3_url,
                                        source="网易云音乐",
                                        quality="128kbps",
                                        extra_info={
                                            "song_id": song_id,
                                            "album": song.get('album', ''),
                                            "pic": song.get('pic', song.get('cover', ''))
                                        }
                                    ))

                        if results:  # 如果找到结果，跳出循环
                            break

                except Exception as api_e:
                    logger.warning(f"API {api_base} 失败: {api_e}")
                    continue

            logger.info(f"网易云音乐 API 找到 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.warning(f"网易云音乐 API 失败: {e}")
            return []

    async def _api_kuwo(self, keyword: str) -> List[SearchResult]:
        """使用酷我音乐 API 搜索"""
        results = []
        try:
            import gzip

            # 酷我音乐搜索 API
            search_url = f"http://search.kuwo.cn/r.s?all={urllib.parse.quote(keyword)}&ft=music&itemset=web_2013&client=kt&pn=0&rn=5&rformat=json&encoding=utf8"

            headers = self._get_headers()
            headers['Accept'] = 'application/json'
            headers['Accept-Encoding'] = 'gzip, deflate'

            req = urllib.request.Request(search_url, headers=headers)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=15, context=self._create_ssl_context())
            )

            # 处理 gzip 压缩
            content = response.read()
            try:
                # 尝试解压 gzip
                content = gzip.decompress(content)
            except:
                pass  # 如果不是 gzip，保持原样

            data = json.loads(content.decode('utf-8', errors='ignore'))

            if data.get('abslist'):
                for item in data['abslist'][:5]:
                    music_id = item.get('MUSICRID', '').replace('MUSIC_', '')
                    if music_id:
                        # 获取播放链接
                        mp3_url = f"http://antiserver.kuwo.cn/anti.s?type=convert_url&rid={music_id}&format=mp3&response=url"

                        mp3_req = urllib.request.Request(mp3_url, headers=headers)
                        mp3_response = await loop.run_in_executor(
                            None,
                            lambda: urllib.request.urlopen(mp3_req, timeout=15, context=self._create_ssl_context())
                        )

                        real_url = mp3_response.read().decode('utf-8', errors='ignore').strip()
                        if real_url and real_url.startswith('http'):
                            results.append(SearchResult(
                                title=f"{item.get('SONGNAME', 'Unknown')} - {item.get('ARTIST', 'Unknown')}",
                                url=real_url,
                                source="酷我音乐",
                                quality="128kbps",
                                extra_info={
                                    "music_id": music_id,
                                    "album": item.get('ALBUM', ''),
                                    "duration": item.get('DURATION', 0)
                                }
                            ))

            logger.info(f"酷我音乐 API 找到 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.warning(f"酷我音乐 API 失败: {e}")
            return []

    async def _search_from_music_websites(self, keyword: str) -> List[SearchResult]:
        """从音乐网站抓取 MP3 链接"""
        results = []

        # 尝试从免费音乐网站抓取
        web_tasks = [
            self._crawl_music_123(keyword),
            self._crawl_music_juice(keyword),
        ]

        web_results = await asyncio.gather(*web_tasks, return_exceptions=True)

        for result in web_results:
            if isinstance(result, list):
                results.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"网页抓取失败: {result}")

        return results

    async def _crawl_music_123(self, keyword: str) -> List[SearchResult]:
        """从 music.123 类网站抓取"""
        # 这是一个示例，实际实现需要根据具体网站结构调整
        return []

    async def _crawl_music_juice(self, keyword: str) -> List[SearchResult]:
        """从 music juice 类网站抓取"""
        # 这是一个示例，实际实现需要根据具体网站结构调整
        return []

    async def _search_video(self, params: Dict) -> str:
        """搜索视频资源"""
        keyword = params.get("keyword", "")

        if not keyword:
            return "❌ 请提供搜索关键词"

        logger.info(f"🎬 搜索视频: {keyword}")

        # 国内视频搜索源
        video_sources = [
            ("bilibili.com", "Bilibili", f"https://search.bilibili.com/all?keyword={urllib.parse.quote(keyword)}"),
            ("douyin.com", "抖音", f"https://www.douyin.com/search/{urllib.parse.quote(keyword)}"),
            ("kuaishou.com", "快手", f"https://www.kuaishou.com/search/video?searchKey={urllib.parse.quote(keyword)}"),
            ("youku.com", "优酷", f"https://so.youku.com/search_video/q_{urllib.parse.quote(keyword)}"),
            ("iqiyi.com", "爱奇艺", f"https://so.iqiyi.com/so/q_{urllib.parse.quote(keyword)}"),
        ]

        result_text = f"🎬 视频搜索结果: {keyword}\n\n"
        for domain, name, url in video_sources:
            result_text += f"• {name}: {url}\n"

        return result_text

    async def _search_image(self, params: Dict) -> str:
        """搜索图片资源"""
        keyword = params.get("keyword", "")

        if not keyword:
            return "❌ 请提供搜索关键词"

        logger.info(f"🖼️ 搜索图片: {keyword}")

        # 图片搜索源
        image_sources = [
            ("baidu.com", "百度图片", f"https://image.baidu.com/search/index?tn=baiduimage&word={urllib.parse.quote(keyword)}"),
            ("bing.com", "必应图片", f"https://www.bing.com/images/search?q={urllib.parse.quote(keyword)}"),
            ("sogou.com", "搜狗图片", f"https://pic.sogou.com/pics?query={urllib.parse.quote(keyword)}"),
            ("360.com", "360图片", f"https://image.so.com/i?q={urllib.parse.quote(keyword)}"),
        ]

        result_text = f"🖼️ 图片搜索结果: {keyword}\n\n"
        for domain, name, url in image_sources:
            result_text += f"• {name}: {url}\n"

        return result_text

    async def _crawl_webpage(self, params: Dict) -> str:
        """抓取网页内容"""
        url = params.get("url", "")
        selector = params.get("selector", "")
        original_text = params.get("original_text", "")

        if not url:
            return "❌ 请提供网页 URL"
        
        # 如果请求包含"页面链接"或"提取链接"，调用链接提取方法
        if "页面链接" in original_text or "提取链接" in original_text or "所有链接" in original_text:
            return await self._extract_page_links(params)
        
        # 如果请求包含"视频链接"，调用视频链接提取方法
        if "视频链接" in original_text or "MP4链接" in original_text.upper():
            return await self._scrape_links(params)

        logger.info(f"🌐 抓取网页: {url}")

        try:
            req = urllib.request.Request(url, headers=self._get_headers())

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=20, context=self._create_ssl_context())
            )

            html = response.read().decode('utf-8', errors='ignore')

            # 提取标题
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Unknown"

            # 提取所有链接
            links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)

            # 提取所有图片
            images = re.findall(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|webp))["\']', html, re.IGNORECASE)

            result = f"🌐 网页抓取结果\n\n"
            result += f"标题: {title}\n"
            result += f"URL: {url}\n"
            result += f"内容长度: {len(html)} 字符\n"
            result += f"链接数量: {len(links)}\n"
            result += f"图片数量: {len(images)}\n\n"

            if links:
                result += "主要链接:\n"
                for link in links[:10]:
                    result += f"  • {link}\n"

            return result

        except Exception as e:
            logger.error(f"网页抓取失败: {e}")
            return f"❌ 网页抓取失败: {str(e)}"

    async def _fetch_api(self, params: Dict) -> str:
        """获取 API 数据"""
        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        data = params.get("data", None)

        if not url:
            return "❌ 请提供 API URL"

        logger.info(f"📡 请求 API: {url}")

        try:
            req_headers = self._get_headers()
            req_headers.update(headers)

            if data and isinstance(data, dict):
                data = json.dumps(data).encode('utf-8')
                req_headers['Content-Type'] = 'application/json'

            req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=20, context=self._create_ssl_context())
            )

            content = response.read().decode('utf-8', errors='ignore')

            # 尝试解析 JSON
            try:
                json_data = json.loads(content)
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
                return f"📡 API 响应\n\n```json\n{formatted[:2000]}\n```"
            except:
                return f"📡 API 响应\n\n{content[:2000]}"

        except Exception as e:
            logger.error(f"API 请求失败: {e}")
            return f"❌ API 请求失败: {str(e)}"

    def _get_task_status(self, params: Dict) -> str:
        """获取任务状态"""
        task_id = params.get("task_id", "")

        if not task_id or task_id not in self.tasks:
            return "❌ 任务不存在"

        task = self.tasks[task_id]

        result = f"🕷️ 任务状态\n\n"
        result += f"任务ID: {task.task_id}\n"
        result += f"类型: {task.task_type}\n"
        result += f"关键词: {task.keyword}\n"
        result += f"状态: {task.status}\n"
        result += f"创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if task.completed_at:
            result += f"完成时间: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if task.error_message:
            result += f"错误信息: {task.error_message}\n"

        result += f"结果数量: {len(task.results)}\n"

        return result

    def _get_task_results(self, params: Dict) -> str:
        """获取任务结果"""
        task_id = params.get("task_id", "")
        limit = params.get("limit", 10)

        if not task_id or task_id not in self.tasks:
            return "❌ 任务不存在"

        task = self.tasks[task_id]

        if not task.results:
            return "📭 暂无结果"

        result = f"📋 任务结果 ({len(task.results)} 个)\n\n"

        for i, r in enumerate(task.results[:limit], 1):
            result += f"{i}. {r.title}\n"
            result += f"   URL: {r.url}\n"
            result += f"   来源: {r.source}\n"
            if r.quality != "unknown":
                result += f"   质量: {r.quality}\n"
            result += "\n"

        return result

    async def _save_results_to_file(self, task_id: str, results: List[SearchResult]):
        """保存结果到文件"""
        try:
            # 创建目录
            data_dir = Path("data") / "crawler"
            data_dir.mkdir(parents=True, exist_ok=True)

            # 保存为 JSON
            file_path = data_dir / f"{task_id}.json"

            data = {
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "source": r.source,
                        "quality": r.quality,
                        "size": r.size,
                        "duration": r.duration,
                        "extra_info": r.extra_info
                    }
                    for r in results
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"结果已保存到: {file_path}")

        except Exception as e:
            logger.error(f"保存结果失败: {e}")

    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = super().get_status()
        status.update({
            "total_tasks": len(self.tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == "failed"),
        })
        return status

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 爬虫智能体

### 功能说明
爬虫智能体专门负责网络爬虫任务，可以搜索网页、抓取内容、下载资源等。

### 支持的操作
- **网页搜索**：搜索互联网上的信息
- **抓取链接**：从网页中提取链接
- **下载资源**：下载视频、图片等文件
- **API数据获取**：调用API获取数据

### 使用示例
- "搜索 Python 教程" - 搜索相关网页
- "搜索新闻 人工智能" - 搜索新闻资讯
- "百度一下 天气" - 使用百度搜索
- "帮我搜一下 菜谱" - 搜索相关信息
- "抓取链接 https://example.com" - 抓取网页中的所有链接
- "下载视频 [视频链接]" - 下载视频文件

### 支持的搜索引擎
- 百度
- 谷歌
- 必应
- 搜狗

### 注意事项
- 部分网站可能需要等待加载
- 下载大文件时请耐心等待
- 请遵守网站的使用条款"""
