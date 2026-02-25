"""
HTTP Request Tool - Simple web requests without Playwright
"""
import json
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus

from .base import BaseTool, ToolResult, tool_registry

REQUESTS_AVAILABLE = False
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    pass

BEAUTIFULSOUP_AVAILABLE = False
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    pass


class HttpRequestTool(BaseTool):
    name = "http_request"
    description = "发送HTTP请求获取网页内容或API数据"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "请求的URL"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "default": "GET",
                "description": "HTTP方法"
            },
            "headers": {
                "type": "object",
                "description": "请求头（可选）"
            },
            "data": {
                "type": "object",
                "description": "POST数据（可选）"
            },
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "超时时间（秒）"
            }
        },
        "required": ["url"]
    }

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> ToolResult:
        if not REQUESTS_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="requests库未安装，请运行: pip install requests"
            )
        
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if headers:
            default_headers.update(headers)

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=default_headers, timeout=timeout)
            else:
                response = requests.post(url, headers=default_headers, json=data, timeout=timeout)
            
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                result = response.json()
                return ToolResult(
                    success=True,
                    output=json.dumps(result, ensure_ascii=False, indent=2)[:5000],
                    data={"status_code": response.status_code, "json": result}
                )
            else:
                text = response.text
                return ToolResult(
                    success=True,
                    output=text[:10000],
                    data={"status_code": response.status_code, "length": len(text)}
                )

        except requests.exceptions.Timeout:
            return ToolResult(success=False, output="", error=f"请求超时（{timeout}秒）")
        except requests.exceptions.RequestException as e:
            return ToolResult(success=False, output="", error=f"请求失败: {str(e)}")


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "获取网页内容并提取正文文本"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "网页URL"
            },
            "selector": {
                "type": "string",
                "description": "CSS选择器，提取特定元素（可选）"
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str, selector: Optional[str] = None) -> ToolResult:
        if not REQUESTS_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="requests库未安装，请运行: pip install requests"
            )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.text, "html.parser")
                
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                if selector:
                    elements = soup.select(selector)
                    text = "\n".join(el.get_text(strip=True) for el in elements)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    text = "\n".join(lines)
            else:
                text = response.text

            return ToolResult(
                success=True,
                output=text[:8000],
                data={"url": url, "length": len(text)}
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"获取网页失败: {str(e)}")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "使用搜索引擎搜索信息（使用DuckDuckGo，无需API密钥）"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "最大结果数"
            }
        },
        "required": ["query"]
    }

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        if not REQUESTS_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="requests库未安装，请运行: pip install requests"
            )

        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            results = []
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.text, "html.parser")
                for result in soup.select(".result")[:max_results]:
                    title_elem = result.select_one(".result__a")
                    snippet_elem = result.select_one(".result__snippet")
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": title_elem.get("href", ""),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                        })
            else:
                results = [{"title": "请安装beautifulsoup4以获得更好的解析", "url": "", "snippet": ""}]

            if not results:
                return ToolResult(
                    success=True,
                    output=f"未找到关于 '{query}' 的结果",
                    data={"query": query, "results": []}
                )

            output_lines = []
            for i, r in enumerate(results, 1):
                output_lines.append(f"【{i}】{r['title']}")
                if r['snippet']:
                    output_lines.append(f"   {r['snippet']}")
                if r['url']:
                    output_lines.append(f"   链接: {r['url']}")
                output_lines.append("")

            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={"query": query, "results": results}
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"搜索失败: {str(e)}")


class NewsFetchTool(BaseTool):
    name = "news_fetch"
    description = "获取最新新闻资讯（从RSS源或新闻网站）"
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["general", "tech", "finance", "world"],
                "default": "general",
                "description": "新闻类别"
            },
            "max_items": {
                "type": "integer",
                "default": 10,
                "description": "最大新闻条数"
            }
        },
        "required": []
    }

    NEWS_SOURCES = {
        "general": [
            "https://news.qq.com/newsgn/rss_newsgn.xml",
            "https://feedx.net/rss/zgxwzk.xml",
        ],
        "tech": [
            "https://www.36kr.com/feed",
            "https://www.ifanr.com/feed",
        ],
        "finance": [
            "https://feedx.net/rss/caijingjie.xml",
        ],
        "world": [
            "https://feedx.net/rss/cankaoxiaoxi.xml",
        ]
    }

    async def execute(self, category: str = "general", max_items: int = 10) -> ToolResult:
        if not REQUESTS_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="requests库未安装，请运行: pip install requests"
            )

        all_news = []
        sources = self.NEWS_SOURCES.get(category, self.NEWS_SOURCES["general"])
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml,application/xml,text/xml",
        }

        for source_url in sources:
            try:
                response = requests.get(source_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                if BEAUTIFULSOUP_AVAILABLE:
                    soup = BeautifulSoup(response.text, "xml")
                    items = soup.find_all("item")
                    
                    for item in items[:max_items]:
                        title = item.find("title")
                        link = item.find("link")
                        desc = item.find("description")
                        pub_date = item.find("pubDate")
                        
                        if title:
                            all_news.append({
                                "title": title.get_text(strip=True),
                                "link": link.get_text(strip=True) if link else "",
                                "description": desc.get_text(strip=True)[:200] if desc else "",
                                "date": pub_date.get_text(strip=True) if pub_date else ""
                            })
            except Exception:
                continue

        if not all_news:
            return ToolResult(
                success=True,
                output="暂时无法获取新闻，请稍后再试",
                data={"category": category, "news": []}
            )

        all_news = all_news[:max_items]
        
        output_lines = [f"📰 {category.upper()} 新闻资讯\n"]
        for i, news in enumerate(all_news, 1):
            output_lines.append(f"【{i}】{news['title']}")
            if news['description']:
                output_lines.append(f"    {news['description']}")
            output_lines.append("")

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={"category": category, "news": all_news, "count": len(all_news)}
        )


def register_http_tools():
    tool_registry.register(HttpRequestTool())
    tool_registry.register(WebFetchTool())
    tool_registry.register(WebSearchTool())
    tool_registry.register(NewsFetchTool())
