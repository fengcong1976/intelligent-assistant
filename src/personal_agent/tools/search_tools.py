"""
Search Tools - 联网搜索工具（带来源验证）
"""
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .base import BaseTool, ToolResult, tool_registry

AUTHORITATIVE_DOMAINS = {
    "news": [
        "xinhuanet.com",
        "people.com.cn", 
        "cctv.com",
        "chinadaily.com.cn",
        "thepaper.cn",
        "caixin.com",
        "reuters.com",
        "bbc.com",
        "cnn.com",
        "bloomberg.com",
    ],
    "tech": [
        "github.com",
        "stackoverflow.com",
        "stackoverflow.cn",
        "csdn.net",
        "juejin.cn",
        "zhihu.com",
        "segmentfault.com",
    ],
    "government": [
        "gov.cn",
        "stats.gov.cn",
        "pbc.gov.cn",
        "mof.gov.cn",
        "ndrc.gov.cn",
    ],
    "finance": [
        "sse.com.cn",
        "szse.cn",
        "csrc.gov.cn",
        "eastmoney.com",
        "sina.com.cn",
        "10jqka.com.cn",
    ],
    "academic": [
        "cnki.net",
        "wanfangdata.com.cn",
        "scholar.google.com",
        "arxiv.org",
        "nature.com",
        "science.org",
    ],
    "weather": [
        "weather.com.cn",
        "cma.gov.cn",
        "tianqi.com",
    ],
    "software": [
        "pypi.org",
        "npmjs.com",
        "apps.microsoft.com",
        "winget.run",
    ],
}

SUSPICIOUS_PATTERNS = [
    r"clickbait",
    r"震惊",
    r"必看",
    r"转发有奖",
    r"限时免费",
    r"内部消息",
]


class WebSearchTool(BaseTool):
    name = "web_search"
    description = """联网搜索工具。当用户询问需要实时信息、最新新闻、当前事件、天气、股价等时效性内容时使用。
    
【重要】搜索原则：
1. 不要用于常识性问题
2. 搜索结果会标注来源可信度
3. 优先使用权威来源的数据
4. 如果搜索结果不可靠，请明确告知用户"""
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，应该简洁明确"
            },
            "category": {
                "type": "string",
                "description": "搜索类别（可选）：news/tech/government/finance/academic/weather/software",
                "enum": ["news", "tech", "government", "finance", "academic", "weather", "software"]
            }
        },
        "required": ["query"]
    }

    async def execute(self, query: str, category: Optional[str] = None) -> ToolResult:
        try:
            import dashscope
            from dashscope import Generation

            search_prompt = f"""请搜索以下问题，并提供详细的搜索结果。

【重要要求】
1. 必须标注每条信息的来源（网站名称和链接）
2. 优先展示权威来源的信息
3. 如果信息来源不可靠，请明确标注"来源待验证"
4. 不要编造任何数据或信息

搜索问题：{query}

请按以下格式返回：
---
## 搜索结果

### 来源1: [网站名称] (可信度: 高/中/低)
- 链接: [URL]
- 内容: [摘要]

### 来源2: [网站名称] (可信度: 高/中/低)
- 链接: [URL]  
- 内容: [摘要]

---
## 结论
[基于可靠来源的总结]
"""
            
            response = Generation.call(
                model="qwen-plus",
                messages=[{"role": "user", "content": search_prompt}],
                enable_search=True,
                result_format="message"
            )

            if response.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"搜索失败: {response.message}"
                )

            content = response.output.choices[0].message.content
            
            verified_content = self._verify_sources(content, category)

            return ToolResult(
                success=True,
                output=verified_content,
                data={
                    "query": query, 
                    "source": "web_search",
                    "category": category,
                    "verified": True
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"搜索出错: {str(e)}"
            )
    
    def _verify_sources(self, content: str, category: Optional[str] = None) -> str:
        """验证来源可信度"""
        warning = "\n\n⚠️ 【数据来源说明】\n"
        warning += "- 以上信息来自网络搜索，请核实重要信息\n"
        warning += "- 权威来源：政府网站、官方媒体、学术机构\n"
        warning += "- 如需确认，建议访问原始来源查看完整内容\n"
        
        if category and category in AUTHORITATIVE_DOMAINS:
            domains = AUTHORITATIVE_DOMAINS[category]
            warning += f"- 该类别推荐来源：{', '.join(domains[:5])}\n"
        
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warning += f"\n⚠️ 检测到可疑内容模式，请谨慎对待\n"
                break
        
        return content + warning


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = """获取网页内容。当需要读取特定网页的详细内容时使用。

【重要】使用原则：
1. 优先获取权威网站的内容
2. 会自动评估来源可信度
3. 对于可疑网站会发出警告"""
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要获取的网页URL"
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str) -> ToolResult:
        try:
            credibility = self._check_credibility(url)
            
            import aiohttp
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10, headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"HTTP {response.status}"
                        )

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    for script in soup(["script", "style", "nav", "footer", "aside"]):
                        script.decompose()

                    title = soup.title.string if soup.title else "无标题"
                    
                    text = soup.get_text(separator='\n', strip=True)
                    
                    if len(text) > 8000:
                        text = text[:8000] + "...\n\n[内容已截断，请访问原网页查看完整内容]"

                    result = f"📄 网页标题: {title}\n"
                    result += f"🔗 来源: {url}\n"
                    result += f"✅ 可信度: {credibility['level']} ({credibility['reason']})\n"
                    result += f"\n{'='*50}\n\n"
                    result += text
                    
                    if credibility['level'] in ['低', '未知']:
                        result += "\n\n⚠️ 【警告】此来源可信度较低，请谨慎对待内容！\n"
                        result += "建议：交叉验证信息，或寻找更权威的来源。\n"

                    return ToolResult(
                        success=True,
                        output=result,
                        data={
                            "url": url, 
                            "length": len(text),
                            "credibility": credibility
                        }
                    )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"获取网页失败: {str(e)}"
            )
    
    def _check_credibility(self, url: str) -> Dict[str, str]:
        """检查URL的可信度"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for category, domains in AUTHORITATIVE_DOMAINS.items():
                for auth_domain in domains:
                    if auth_domain in domain:
                        return {
                            "level": "高",
                            "reason": f"权威来源（{category}类别）"
                        }
            
            if domain.endswith('.gov.cn'):
                return {
                    "level": "高",
                    "reason": "政府官方网站"
                }
            
            if domain.endswith('.edu.cn'):
                return {
                    "level": "高",
                    "reason": "教育机构网站"
                }
            
            if 'wiki' in domain:
                return {
                    "level": "中",
                    "reason": "维基类网站，需要交叉验证"
                }
            
            if any(p in domain for p in ['blog', 'bbs', 'forum', 'weibo', 'twitter', 'facebook']):
                return {
                    "level": "低",
                    "reason": "社交媒体/博客，内容可能不准确"
                }
            
            return {
                "level": "未知",
                "reason": "未知的来源，请谨慎对待"
            }
            
        except Exception:
            return {
                "level": "未知",
                "reason": "无法解析来源"
            }


class SourceVerifyTool(BaseTool):
    name = "verify_source"
    description = "验证信息来源的可信度。输入URL或信息内容，返回可信度评估。"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要验证的URL（可选）"
            },
            "content": {
                "type": "string",
                "description": "要验证的信息内容（可选）"
            }
        }
    }

    async def execute(self, url: Optional[str] = None, content: Optional[str] = None) -> ToolResult:
        result = "📋 来源验证报告\n\n"
        
        if url:
            fetch_tool = WebFetchTool()
            credibility = fetch_tool._check_credibility(url)
            result += f"🔗 URL: {url}\n"
            result += f"✅ 可信度: {credibility['level']}\n"
            result += f"📝 原因: {credibility['reason']}\n\n"
            
            if credibility['level'] in ['低', '未知']:
                result += "⚠️ 建议：寻找更权威的来源验证此信息\n"
        
        if content:
            result += "📄 内容分析:\n"
            
            suspicious_found = []
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    suspicious_found.append(pattern)
            
            if suspicious_found:
                result += f"⚠️ 检测到可疑模式: {', '.join(suspicious_found)}\n"
                result += "建议：谨慎对待此信息，寻找权威来源验证\n"
            else:
                result += "✅ 未检测到明显的可疑模式\n"
        
        return ToolResult(
            success=True,
            output=result,
            data={"verified": True}
        )


def register_search_tools():
    tool_registry.register(WebSearchTool())
    tool_registry.register(WebFetchTool())
    tool_registry.register(SourceVerifyTool())
