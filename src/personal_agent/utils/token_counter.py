"""
Token Counter - 全局Token统计
"""
from typing import Optional
from loguru import logger


class TokenCounter:
    """全局Token计数器"""
    _instance: Optional['TokenCounter'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._total_tokens = 0
        self._callback = None
    
    def set_callback(self, callback):
        """设置更新回调函数"""
        self._callback = callback
    
    def clear_callback(self):
        """清除回调函数"""
        self._callback = None
    
    def add_tokens(self, tokens: int):
        """添加Token"""
        if tokens > 0:
            self._total_tokens += tokens
            if self._callback:
                try:
                    import weakref
                    if hasattr(self._callback, '__self__'):
                        obj = self._callback.__self__
                        if hasattr(obj, 'isDeleted'):
                            if obj.isDeleted():
                                self._callback = None
                                return
                    self._callback(tokens)
                except RuntimeError:
                    self._callback = None
                except Exception as e:
                    self._callback = None
    
    def get_total_tokens(self) -> int:
        """获取总Token数"""
        return self._total_tokens
    
    def reset(self):
        """重置计数器"""
        self._total_tokens = 0


token_counter = TokenCounter()


def update_token_count(tokens: int):
    """更新Token计数（全局函数）"""
    token_counter.add_tokens(tokens)
