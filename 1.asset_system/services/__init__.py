"""
Services模块
业务服务层
"""

__all__ = [
    'AuthManager',
    'GeocodingService',
]


def AuthManager(*args, **kwargs):
    """延迟导入 AuthManager"""
    from .auth import AuthManager as _AuthManager
    return _AuthManager(*args, **kwargs)


def GeocodingService(*args, **kwargs):
    """延迟导入 GeocodingService"""
    from .geocoding import GeocodingService as _GeocodingService
    return _GeocodingService(*args, **kwargs)
