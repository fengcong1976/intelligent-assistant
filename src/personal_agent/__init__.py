"""
Personal AI Agent - A modular personal assistant framework
"""

import sys

_src_modules = [k for k in sys.modules.keys() if k.startswith('src.personal_agent')]
for k in _src_modules:
    del sys.modules[k]

__version__ = "0.1.0"
