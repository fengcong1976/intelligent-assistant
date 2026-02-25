"""
Search Plugin - 搜索插件（使用新框架）
"""
from typing import Any, Dict

from ..base import Plugin, PluginContext, PluginResult, PluginPriority


class SearchPlugin(Plugin):
    """联网搜索插件"""

    name = "web_search"
    description = "联网搜索实时信息"
    version = "1.0.0"
    priority = PluginPriority.NORMAL
    timeout = 15.0

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            }
        },
        "required": ["query"]
    }

    async def _setup(self):
        """初始化"""
        from ...config import settings
        self.api_key = settings.llm.dashscope_api_key

    async def execute(self, context: PluginContext) -> PluginResult:
        """执行搜索"""
        query = context.get("query") or context.input_data

        if not query:
            return PluginResult(
                success=False,
                error="搜索关键词不能为空"
            )

        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.api_key

            response = Generation.call(
                model="qwen-plus",
                messages=[{"role": "user", "content": str(query)}],
                enable_search=True,
                result_format="message"
            )

            if response.status_code != 200:
                return PluginResult(
                    success=False,
                    error=f"搜索失败: {response.message}"
                )

            content = response.output.choices[0].message.content

            return PluginResult(
                success=True,
                output=content,
                metadata={"query": query, "source": "web_search"}
            )

        except Exception as e:
            return PluginResult(
                success=False,
                error=f"搜索出错: {str(e)}"
            )


class FetchPlugin(Plugin):
    """网页获取插件"""

    name = "web_fetch"
    description = "获取网页内容"
    version = "1.0.0"
    priority = PluginPriority.NORMAL
    timeout = 10.0

    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "网页URL"
            }
        },
        "required": ["url"]
    }

    async def execute(self, context: PluginContext) -> PluginResult:
        """获取网页"""
        url = context.get("url")

        if not url:
            return PluginResult(
                success=False,
                error="URL不能为空"
            )

        try:
            import aiohttp
            from bs4 import BeautifulSoup

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return PluginResult(
                            success=False,
                            error=f"HTTP {response.status}"
                        )

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # 移除脚本和样式
                    for script in soup(["script", "style"]):
                        script.decompose()

                    text = soup.get_text(separator='\n', strip=True)

                    # 限制长度
                    if len(text) > 5000:
                        text = text[:5000] + "..."

                    return PluginResult(
                        success=True,
                        output=text,
                        metadata={"url": url, "length": len(text)}
                    )

        except Exception as e:
            return PluginResult(
                success=False,
                error=f"获取网页失败: {str(e)}"
            )
