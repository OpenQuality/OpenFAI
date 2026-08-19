"""
CSRF中间件 - 动态信任开发环境域名
"""
import re
from django.conf import settings


class DynamicCSRFMiddleware:
    """
    动态CSRF信任中间件
    自动信任来自本地开发环境的请求
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 获取请求的origin或referer
        origin = request.META.get('HTTP_ORIGIN', '')
        referer = request.META.get('HTTP_REFERER', '')

        # 信任本地开发环境
        trusted_patterns = [
            r'http://localhost:\d+',
            r'http://127\.0\.0\.1:\d+',
        ]

        is_trusted = False
        for pattern in trusted_patterns:
            if re.match(pattern, origin) or re.match(pattern, referer):
                is_trusted = True
                break

        # 如果来自信任域名，动态添加到信任列表
        if is_trusted and origin:
            if origin not in settings.CSRF_TRUSTED_ORIGINS:
                settings.CSRF_TRUSTED_ORIGINS.append(origin)

        response = self.get_response(request)
        return response
