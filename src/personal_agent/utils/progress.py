"""
Progress Callback Manager - 进度回调管理器

用于在工具执行时向GUI报告进度
"""
from typing import Callable, Optional


class ProgressManager:
    """全局进度管理器"""

    def __init__(self):
        self._callback: Optional[Callable[[str, int], None]] = None

    def set_callback(self, callback: Callable[[str, int], None]):
        """设置进度回调函数
        Args:
            callback: 回调函数 (message, progress)
                     progress: -1 表示不确定进度，0-100 表示百分比
        """
        self._callback = callback

    def clear_callback(self):
        """清除回调函数"""
        self._callback = None

    def report(self, message: str, progress: int = -1):
        """报告进度
        Args:
            message: 进度消息
            progress: 进度百分比，-1 表示不确定
        """
        if self._callback:
            try:
                self._callback(message, progress)
            except Exception:
                pass


# 全局进度管理器实例
progress_manager = ProgressManager()
