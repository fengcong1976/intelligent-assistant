"""
新闻资讯智能体 - 收集和整理新闻资讯
支持多源新闻抓取、摘要生成、分类整理
"""
import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from ..base import BaseAgent, Task


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    url: str
    source: str
    publish_time: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NewsAgent(BaseAgent):
    """新闻资讯智能体 - 收集新闻资讯"""
    
    KEYWORD_MAPPINGS = {
        "新闻": ("fetch_news", {}),
        "热点": ("fetch_hot", {}),
        "今日新闻": ("fetch_news", {}),
        "今日热点": ("fetch_hot", {}),
        "最新新闻": ("fetch_news", {}),
        "最新热点": ("fetch_hot", {}),
        "看新闻": ("fetch_news", {}),
        "看热点": ("fetch_hot", {}),
        "科技新闻": ("fetch_news", {"category": "tech"}),
        "财经新闻": ("fetch_news", {"category": "finance"}),
    }
    
    # 新闻源配置 - 使用RSS源更稳定
    NEWS_SOURCES = {
        "36氪": {
            "url": "https://36kr.com/feed",
            "type": "rss",
        },
        "虎嗅": {
            "url": "https://www.huxiu.com/rss/0.xml",
            "type": "rss",
        },
        "少数派": {
            "url": "https://sspai.com/feed",
            "type": "rss",
        },
        "IT之家": {
            "url": "https://www.ithome.com/rss/",
            "type": "rss",
        },
        "爱范儿": {
            "url": "https://www.ifanr.com/feed",
            "type": "rss",
        },
        "钛媒体": {
            "url": "https://www.tmtpost.com/rss.xml",
            "type": "rss",
        },
        "开源中国": {
            "url": "https://www.oschina.net/news/rss",
            "type": "rss",
        },
        "InfoQ": {
            "url": "https://www.infoq.cn/feed",
            "type": "rss",
        },
    }
    
    # 备用新闻API源
    API_SOURCES = [
        "https://www.zhihu.com/api/v3/feed/topstory",
    ]
    
    def __init__(self):
        super().__init__(
            name="news_agent",
            description="新闻资讯智能体 - 收集和整理新闻资讯"
        )
        
        self.register_capability(
            capability="get_news",
            description="获取新闻资讯。可以获取热点新闻或特定类别的新闻。",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "新闻类别（可选），如'科技'、'财经'、'体育'",
                        "default": "热点"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回新闻条数",
                        "default": 5
                    }
                },
                "required": []
            },
            category="news"
        )
        
        self.news_cache: List[NewsItem] = []
        self.cache_time: Optional[datetime] = None
        self.cache_duration = 1800
        self._session: Optional[aiohttp.ClientSession] = None
        self._llm_gateway = None
        
        logger.info("📰 新闻资讯智能体已初始化")
    
    def _get_llm_gateway(self):
        """获取 LLM 网关"""
        if self._llm_gateway is None:
            from ...llm import LLMGateway
            from ...config import settings
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        llm = self._get_llm_gateway()
        messages = [{"role": "user", "content": prompt}]
        response = await llm.chat(messages)
        return response.content
    
    async def start(self):
        """启动智能体"""
        await super().start()
        
        # 创建 SSL 上下文，忽略证书验证
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ssl=ssl_context)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
    
    async def stop(self):
        """停止智能体"""
        if self._session:
            await self._session.close()
        await super().stop()
    
    async def execute_task(self, task: Task) -> str:
        """执行任务"""
        task_type = task.type
        action = task.params.get("action", "").lower()
        params = task.params
        
        if task_type == "get_news" or task_type == "fetch_news":
            action = "fetch_news"
        elif not action:
            action = "fetch_news"
        
        logger.info(f"📰 News Agent 执行: {action}")
        
        try:
            if action in ["fetch_news", "news_fetch", "get_news"]:
                return await self._fetch_news(
                    count=params.get("count", 10),
                    category=params.get("category"),
                    source=params.get("source")
                )
            elif action in ["fetch_hot", "news_hot"]:
                return await self._fetch_hot_news(count=params.get("count", 10))
            elif action in ["search_news", "news_search"]:
                return await self._search_news(
                    keyword=params.get("keyword"),
                    count=params.get("count", 10)
                )
            elif action == "get_categories":
                return await self._get_categories()
            elif action == "get_sources":
                return await self._get_sources()
            else:
                return f"❌ 未知的操作: {action}"
        
        except Exception as e:
            logger.error(f"News Agent 执行失败: {e}")
            return f"❌ 操作失败: {str(e)}"
    
    async def _fetch_news(self, count: int = 20, category: Optional[str] = None, 
                         source: Optional[str] = None) -> str:
        """获取新闻资讯"""
        # 检查缓存
        if self._is_cache_valid() and self.news_cache:
            news_list = self._get_from_cache(count, category)
            return await self._generate_news_brief(news_list)
        
        all_news = []
        
        # 从多个源抓取新闻
        sources_to_fetch = {source: config} if source and source in self.NEWS_SOURCES else self.NEWS_SOURCES
        
        for source_name, config in sources_to_fetch.items():
            try:
                # 每个源获取更多新闻
                news = await self._fetch_from_source(source_name, config, 15)
                all_news.extend(news)
                logger.info(f"📰 从 {source_name} 获取 {len(news)} 条新闻")
            except Exception as e:
                logger.warning(f"从 {source_name} 获取新闻失败: {e}")
        
        # 如果RSS源都失败了，尝试知乎热榜作为备用
        if not all_news:
            logger.info("📰 RSS源获取失败，尝试知乎热榜作为备用...")
            try:
                zhihu_news = await self._fetch_zhihu_hot(count)
                all_news.extend(zhihu_news)
            except Exception as e:
                logger.warning(f"知乎热榜获取失败: {e}")
        
        # 去重（基于标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            if news.title and news.title not in seen_titles:
                seen_titles.add(news.title)
                unique_news.append(news)
        
        # 过滤今天的新闻
        today = datetime.now().date()
        today_news = []
        for news in unique_news:
            if news.publish_time:
                try:
                    # 尝试解析发布时间
                    from email.utils import parsedate_to_datetime
                    pub_date = parsedate_to_datetime(news.publish_time)
                    if pub_date.date() == today:
                        today_news.append(news)
                except:
                    # 如果无法解析时间，保留该新闻（可能是最新发布的）
                    today_news.append(news)
            else:
                # 没有发布时间的新闻也保留
                today_news.append(news)
        
        # 如果今天的新闻太少，使用所有新闻
        if len(today_news) < 3:
            today_news = unique_news
            title_suffix = "最新新闻资讯"
        else:
            today_news = today_news
            title_suffix = f"今日新闻 ({today.strftime('%Y-%m-%d')})"
        
        # 更新缓存
        self.news_cache = today_news
        self.cache_time = datetime.now()
        
        # 返回指定数量的新闻，使用LLM生成简报
        result_news = today_news[:count]
        return await self._generate_news_brief(result_news)
    
    async def _fetch_hot_news(self, count: int = 10) -> str:
        """获取热点新闻"""
        # 尝试从多个源获取热门新闻
        hot_news = []
        
        # 知乎热榜
        try:
            zhihu_hot = await self._fetch_zhihu_hot(count)
            hot_news.extend(zhihu_hot)
        except Exception as e:
            logger.warning(f"获取知乎热榜失败: {e}")
        
        # 如果知乎热榜不够，从新闻源补充
        if len(hot_news) < count:
            try:
                await self._fetch_news(count)
                hot_news.extend(self.news_cache[:count - len(hot_news)])
            except Exception as e:
                logger.warning(f"获取新闻失败: {e}")
        
        # 去重并排序
        seen = set()
        unique_hot = []
        for news in hot_news:
            if news.title not in seen:
                seen.add(news.title)
                unique_hot.append(news)
        
        # 使用LLM生成热点简报
        return await self._generate_hot_brief(unique_hot[:count])
    
    async def _fetch_zhihu_hot(self, count: int = 10) -> List[NewsItem]:
        """获取知乎热榜"""
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                news_list = []
                
                for item in data.get("data", [])[:count]:
                    target = item.get("target", {})
                    news = NewsItem(
                        title=target.get("title", ""),
                        url=target.get("url", ""),
                        source="知乎热榜",
                        summary=target.get("excerpt", "")[:100] + "..." if target.get("excerpt") else None
                    )
                    news_list.append(news)
                
                return news_list
        except Exception as e:
            logger.error(f"获取知乎热榜失败: {e}")
            return []
    
    async def _fetch_from_source(self, source_name: str, config: Dict, count: int) -> List[NewsItem]:
        """从指定源抓取新闻"""
        news_list = []
        
        try:
            async with self._session.get(config["url"]) as response:
                if response.status != 200:
                    logger.warning(f"{source_name} 返回状态码: {response.status}")
                    return []
                
                content = await response.text()
                
                # 检查是否是RSS源
                if config.get("type") == "rss" or "rss" in config["url"] or "feed" in config["url"]:
                    news_list = self._parse_rss(content, source_name, count)
                else:
                    # HTML解析
                    soup = BeautifulSoup(content, 'html.parser')
                    links = soup.select(config.get("selector", "a"))
                    
                    for link in links[:count]:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if not title or not href:
                            continue
                        
                        # 处理相对URL
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = urljoin(config.get("base_url", ""), href)
                        elif not href.startswith('http'):
                            href = urljoin(config.get("base_url", ""), href)
                        
                        news = NewsItem(
                            title=title,
                            url=href,
                            source=source_name
                        )
                        news_list.append(news)
        
        except Exception as e:
            logger.error(f"从 {source_name} 抓取新闻失败: {e}")
        
        return news_list
    
    def _parse_rss(self, content: str, source_name: str, count: int) -> List[NewsItem]:
        """解析RSS/Atom订阅"""
        news_list = []
        
        try:
            soup = BeautifulSoup(content, 'xml')
            
            # 尝试RSS格式
            items = soup.find_all('item')
            if not items:
                # 尝试Atom格式
                items = soup.find_all('entry')
            
            for item in items[:count]:
                # 获取标题
                title_tag = item.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ""
                
                # 获取链接
                link_tag = item.find('link')
                if link_tag:
                    href = link_tag.get('href') or link_tag.get_text(strip=True)
                else:
                    href = ""
                
                # 获取描述/摘要
                desc_tag = item.find('description') or item.find('summary')
                summary = ""
                if desc_tag:
                    summary = desc_tag.get_text(strip=True)[:200]
                    if len(summary) > 100:
                        summary = summary[:100] + "..."
                
                # 获取发布时间
                time_tag = item.find('pubDate') or item.find('published') or item.find('updated')
                pub_time = time_tag.get_text(strip=True) if time_tag else None
                
                if title and href:
                    news = NewsItem(
                        title=title,
                        url=href,
                        source=source_name,
                        summary=summary if summary else None,
                        publish_time=pub_time
                    )
                    news_list.append(news)
            
            logger.info(f"📰 从 {source_name} RSS解析到 {len(news_list)} 条新闻")
            
        except Exception as e:
            logger.error(f"解析RSS失败: {e}")
        
        return news_list
    
    async def _search_news(self, keyword: Optional[str], count: int = 10) -> str:
        """搜索新闻"""
        if not keyword:
            return "❌ 请提供搜索关键词"
        
        # 先获取最新新闻
        await self._fetch_news(count * 2)
        
        # 过滤包含关键词的新闻
        filtered = [
            news for news in self.news_cache
            if keyword.lower() in news.title.lower() or 
               (news.summary and keyword.lower() in news.summary.lower())
        ]
        
        if not filtered:
            return f"🔍 未找到包含 '{keyword}' 的新闻"
        
        return self._format_news_output(filtered[:count], f"🔍 搜索 '{keyword}' 的结果 (共{len(filtered[:count])}条)")
    
    async def _get_categories(self) -> str:
        """获取新闻分类"""
        categories = ["国内", "国际", "财经", "科技", "体育", "娱乐", "社会", "军事"]
        return "📂 新闻分类:\n" + "\n".join(f"  • {cat}" for cat in categories)
    
    async def _get_sources(self) -> str:
        """获取新闻源"""
        sources = list(self.NEWS_SOURCES.keys())
        return "📡 新闻源:\n" + "\n".join(f"  • {source}" for source in sources)
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cache_time or not self.news_cache:
            return False
        elapsed = (datetime.now() - self.cache_time).total_seconds()
        return elapsed < self.cache_duration
    
    def _get_from_cache(self, count: int, category: Optional[str] = None) -> List[NewsItem]:
        """从缓存获取新闻"""
        news_list = self.news_cache
        if category:
            news_list = [n for n in news_list if n.category == category]
        return news_list[:count]
    
    def _format_news_output(self, news_list: List[NewsItem], title: str) -> str:
        """格式化新闻输出"""
        if not news_list:
            return "📰 暂无新闻资讯"
        
        lines = [f"{title}\n"]
        
        for i, news in enumerate(news_list, 1):
            lines.append(f"{i}. {news.title}")
            if news.summary:
                lines.append(f"   📝 {news.summary}")
            lines.append(f"   📡 {news.source}")
            if news.url:
                lines.append(f"   🔗 {news.url}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def _generate_news_brief(self, news_list: List[NewsItem]) -> str:
        """使用LLM生成新闻简报"""
        if not news_list:
            return "📰 暂无新闻资讯"
        
        # 构建新闻内容
        news_content = "\n".join([
            f"{i+1}. 【{n.source}】{n.title}\n   {n.summary or ''}"
            for i, n in enumerate(news_list[:30])
        ])
        
        prompt = f"""请根据以下新闻内容，生成一份简洁的新闻简报。

新闻内容：
{news_content}

请按以下格式输出：

## 📰 今日新闻简报

### 🔥 热点关注
（列出3-5条最重要的新闻，每条用一句话概括）

### 📊 行业动态
（科技、财经等领域的新闻摘要）

### 💡 简报总结
（用2-3句话总结今天的主要新闻趋势）

注意：
1. 提取核心信息，去除冗余内容
2. 保持简洁，每条摘要不超过50字
3. 按重要性排序
4. 使用简洁的中文表达"""

        try:
            brief = await self._call_llm(prompt)
            return brief
        except Exception as e:
            logger.error(f"生成新闻简报失败: {e}")
            return self._format_news_output(news_list, "📰 今日新闻")
    
    async def _generate_hot_brief(self, news_list: List[NewsItem]) -> str:
        """使用LLM生成热点新闻简报"""
        if not news_list:
            return "🔥 暂无热点新闻"
        
        # 构建新闻内容
        news_content = "\n".join([
            f"{i+1}. {n.title}\n   {n.summary or ''}"
            for i, n in enumerate(news_list[:20])
        ])
        
        prompt = f"""请根据以下热点新闻内容，生成一份简洁的热点简报。

热点内容：
{news_content}

请按以下格式输出：

## 🔥 今日热点

### 📌 热点速览
（用一句话概括每条热点，按热度排序）

### 💬 热点解读
（挑选2-3个最重要的热点进行简要解读）

注意：
1. 突出重点，简洁明了
2. 每条热点概括不超过30字
3. 保留新闻的核心信息"""

        try:
            brief = await self._call_llm(prompt)
            return brief
        except Exception as e:
            logger.error(f"生成热点简报失败: {e}")
            return self._format_news_output(news_list, "🔥 热点新闻")
    
    def get_capabilities(self) -> list:
        """获取能力列表"""
        return [
            "news_fetch",
            "news_search",
            "hot_news",
            "news_summary"
        ]
