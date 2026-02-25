"""
Tool Doc Manager - 工具文档管理器

负责管理工具文档（TOOL.md）的加载、缓存和查询
"""
from typing import Optional, Dict, List
from pathlib import Path
from loguru import logger
import json


class ToolDocManager:
    """
    工具文档管理器
    
    功能：
    1. 按需加载工具文档
    2. 缓存已加载的文档
    3. 统计工具使用频率
    4. 智能判断是否应该在system prompt中包含完整文档
    """
    
    def __init__(self, tools_dir: str = None):
        if tools_dir is None:
            from ..config import settings
            tools_dir = Path(__file__).parent.parent / 'agents'
        
        self.tools_dir = Path(tools_dir)
        self.doc_cache: Dict[str, str] = {}
        self.access_count: Dict[str, int] = {}
        self.cache_file = Path.home() / '.personal_agent' / 'tool_doc_cache.json'
        
        self._load_cache()
        logger.info(f"📚 工具文档管理器已初始化，工具目录: {self.tools_dir}")
    
    def _load_cache(self):
        """从文件加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.access_count = cache_data.get('access_count', {})
                logger.debug(f"📚 已加载工具访问统计: {len(self.access_count)} 个工具")
            except Exception as e:
                logger.warning(f"📚 加载缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({'access_count': self.access_count}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"📚 保存缓存失败: {e}")
    
    def get_tool_doc(self, tool_name: str, force_load: bool = False) -> Optional[str]:
        """
        获取工具文档
        
        Args:
            tool_name: 工具名称
            force_load: 是否强制重新加载
        
        Returns:
            工具文档内容，如果不存在则返回None
        """
        if tool_name not in self.doc_cache or force_load:
            doc_path = self.tools_dir / f'{tool_name}_tool.md'
            
            if doc_path.exists():
                try:
                    self.doc_cache[tool_name] = doc_path.read_text(encoding='utf-8')
                    logger.debug(f"📚 加载工具文档: {tool_name}")
                except Exception as e:
                    logger.error(f"📚 加载工具文档失败 {tool_name}: {e}")
                    return None
            else:
                logger.debug(f"📚 工具文档不存在: {tool_name}")
                return None
        
        self.access_count[tool_name] = self.access_count.get(tool_name, 0) + 1
        
        if self.access_count[tool_name] % 10 == 0:
            self._save_cache()
        
        return self.doc_cache.get(tool_name)
    
    def get_tool_summary(self, tool_name: str, registry=None) -> Optional[str]:
        """
        获取工具摘要（不加载完整文档）
        
        Args:
            tool_name: 工具名称
            registry: 工具注册中心（可选）
        
        Returns:
            工具摘要，如果找不到则返回None
        """
        if registry:
            tool = registry.get_tool(tool_name)
            if tool:
                return f"{tool.name}: {tool.description}"
        
        return None
    
    def should_include_full_doc(self, tool_name: str, threshold: int = 10) -> bool:
        """
        判断是否应该在system prompt中包含完整文档
        
        Args:
            tool_name: 工具名称
            threshold: 使用次数阈值，默认10次
        
        Returns:
            是否应该包含完整文档
        """
        return self.access_count.get(tool_name, 0) >= threshold
    
    def get_frequent_tools(self, top_n: int = 5, threshold: int = 5) -> List[str]:
        """
        获取最常用的工具
        
        Args:
            top_n: 返回前N个工具
            threshold: 最小使用次数阈值
        
        Returns:
            工具名称列表，按使用次数降序排列
        """
        filtered_tools = {
            tool: count 
            for tool, count in self.access_count.items() 
            if count >= threshold
        }
        
        sorted_tools = sorted(
            filtered_tools.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [tool for tool, _ in sorted_tools[:top_n]]
    
    def get_all_available_docs(self) -> List[str]:
        """
        获取所有可用的工具文档
        
        Returns:
            工具名称列表
        """
        available_docs = []
        
        if self.tools_dir.exists():
            for doc_file in self.tools_dir.glob('*_tool.md'):
                tool_name = doc_file.stem.replace('_tool', '')
                available_docs.append(tool_name)
        
        return available_docs
    
    def clear_cache(self, tool_name: str = None):
        """
        清除缓存
        
        Args:
            tool_name: 工具名称，如果为None则清除所有缓存
        """
        if tool_name:
            if tool_name in self.doc_cache:
                del self.doc_cache[tool_name]
                logger.debug(f"📚 清除工具缓存: {tool_name}")
        else:
            self.doc_cache.clear()
            logger.debug(f"📚 清除所有工具缓存")
    
    def get_usage_stats(self) -> Dict[str, int]:
        """
        获取工具使用统计
        
        Returns:
            工具使用次数字典
        """
        return self.access_count.copy()
    
    def format_frequent_docs_for_prompt(self, registry=None, top_n: int = 3) -> str:
        """
        格式化常用工具文档用于system prompt
        
        Args:
            registry: 工具注册中心
            top_n: 包含前N个常用工具
        
        Returns:
            格式化后的字符串
        """
        frequent_tools = self.get_frequent_tools(top_n=top_n)
        
        if not frequent_tools:
            return ""
        
        result_parts = []
        for tool_name in frequent_tools:
            doc = self.get_tool_doc(tool_name)
            if doc:
                result_parts.append(f"\n【{tool_name}】\n{doc}")
        
        return "\n".join(result_parts)
    
    def format_tool_list_for_prompt(self, registry) -> str:
        """
        格式化工具列表用于system prompt
        
        Args:
            registry: 工具注册中心
        
        Returns:
            格式化后的字符串
        """
        tools = registry.get_all_tools()
        
        tool_list = []
        for tool in tools:
            summary = self.get_tool_summary(tool.name, registry)
            if summary:
                tool_list.append(f"- {summary}")
        
        return "可用工具列表:\n" + "\n".join(tool_list)
