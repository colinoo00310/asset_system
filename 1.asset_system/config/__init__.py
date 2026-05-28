"""
Config模块
提供配置相关的统一管理
"""

from .database import Database
from .map_config import get_baidu_ak, get_amap_key, set_keys

__all__ = [
    'Database',
    'get_baidu_ak',
    'get_amap_key',
    'set_keys',
]
