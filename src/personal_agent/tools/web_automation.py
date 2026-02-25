"""
Web Automation Tool using Playwright
"""
import asyncio
import logging
from typing import Optional, List

from .base import BaseTool, ToolResult, tool_registry

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


class WebBrowserTool(BaseTool):
    name = "web_browser"
    description = "打开网页并进行操作"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "type", "screenshot", "extract", "scroll"],
                "description": "操作类型"
            },
            "url": {
                "type": "string",
                "description": "网页URL（navigate时需要）"
            },
            "selector": {
                "type": "string",
                "description": "CSS选择器（click/type时需要）"
            },
            "text": {
                "type": "string",
                "description": "要输入的文本（type时需要）"
            },
            "wait_time": {
                "type": "integer",
                "description": "等待时间（毫秒）",
                "default": 1000
            }
        },
        "required": ["action"]
    }

    _browser = None
    _page = None

    async def _ensure_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright未安装或不可用，请运行: pip install playwright && playwright install chromium")
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        wait_time: int = 1000
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="Playwright未安装，网页自动化功能不可用"
            )
        try:
            await self._ensure_browser()

            if action == "navigate":
                if not url:
                    return ToolResult(
                        success=False,
                        output="",
                        error="URL is required for navigate action"
                    )
                await self._page.goto(url)
                await self._page.wait_for_timeout(wait_time)
                return ToolResult(
                    success=True,
                    output=f"Navigated to {url}",
                    data={"url": url, "title": await self._page.title()}
                )

            elif action == "click":
                if not selector:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Selector is required for click action"
                    )
                await self._page.click(selector)
                await self._page.wait_for_timeout(wait_time)
                return ToolResult(
                    success=True,
                    output=f"Clicked element: {selector}"
                )

            elif action == "type":
                if not selector or not text:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Selector and text are required for type action"
                    )
                await self._page.fill(selector, text)
                return ToolResult(
                    success=True,
                    output=f"Typed text into: {selector}"
                )

            elif action == "screenshot":
                screenshot_bytes = await self._page.screenshot()
                return ToolResult(
                    success=True,
                    output="Screenshot captured",
                    data={"size": len(screenshot_bytes)}
                )

            elif action == "extract":
                content = await self._page.content()
                text_content = await self._page.inner_text("body")
                return ToolResult(
                    success=True,
                    output=text_content[:5000],
                    data={"html_length": len(content), "text_length": len(text_content)}
                )

            elif action == "scroll":
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await self._page.wait_for_timeout(wait_time)
                return ToolResult(
                    success=True,
                    output="Scrolled down one page"
                )

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Web automation failed: {str(e)}"
            )

    @classmethod
    async def close(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            cls._page = None


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "搜索网页内容"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "engine": {
                "type": "string",
                "enum": ["google", "bing", "baidu"],
                "default": "baidu",
                "description": "搜索引擎"
            }
        },
        "required": ["query"]
    }

    _browser = None
    _page = None

    async def _ensure_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright未安装或不可用")
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()

    async def execute(self, query: str, engine: str = "baidu") -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="Playwright未安装，网页搜索功能不可用"
            )
        try:
            await self._ensure_browser()

            search_urls = {
                "google": f"https://www.google.com/search?q={query}",
                "bing": f"https://www.bing.com/search?q={query}",
                "baidu": f"https://www.baidu.com/s?wd={query}"
            }

            url = search_urls.get(engine, search_urls["baidu"])
            await self._page.goto(url)
            await self._page.wait_for_timeout(2000)

            results = await self._page.evaluate("""
                () => {
                    const results = [];
                    const items = document.querySelectorAll('h3, .result, .c-container');
                    items.forEach((item, index) => {
                        const link = item.closest('a') || item.querySelector('a');
                        if (link && item.textContent) {
                            results.push({
                                title: item.textContent.trim(),
                                link: link.href
                            });
                        }
                    });
                    return results.slice(0, 10);
                }
            """)

            output_lines = []
            for i, r in enumerate(results[:10], 1):
                output_lines.append(f"{i}. {r['title']}\n   {r['link']}")

            return ToolResult(
                success=True,
                output="\n\n".join(output_lines),
                data={"results": results[:10], "engine": engine}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Web search failed: {str(e)}"
            )

    @classmethod
    async def close(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            cls._page = None


def register_web_tools():
    if PLAYWRIGHT_AVAILABLE:
        tool_registry.register(WebBrowserTool())
        tool_registry.register(WebSearchTool())
    else:
        logger.debug("Playwright not available, web tools disabled")
