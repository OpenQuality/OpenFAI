"""
Django 6.0兼容性修复
DRF的DefaultRouter在Django 6.0中存在format_suffix_patterns重复注册问题
"""
from rest_framework.routers import DefaultRouter as DRFDefaultRouter


class DefaultRouter(DRFDefaultRouter):
    """
    兼容Django 6.0的DefaultRouter
    禁用format_suffix_patterns以避免converter重复注册错误
    """
    def get_urls(self):
        """
        生成URL列表，但跳过format_suffix_patterns
        """
        # 调用父类方法获取基础URLs
        urls = super(DRFDefaultRouter, self).get_urls()
        # 不调用format_suffix_patterns，直接返回urls
        return urls

