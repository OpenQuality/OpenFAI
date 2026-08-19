"""
URL configuration for FAI System project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import JsonResponse


def health_check(request):
    """健康检查端点"""
    return JsonResponse({"status": "ok", "service": "fai-system"})


urlpatterns = [
    path('admin/', admin.site.urls),
    # 健康检查
    path('v1/ping', health_check),
    # API路由
    path('api/v1/accounts/', include('accounts.api_urls')),
    path('api/v1/parts/', include('parts.api_urls')),
    path('api/v1/inspections/', include('inspections.urls')),
    path('api/v1/measurements/', include('measurements.urls')),
    path('api/v1/reports/', include('reports.api_urls')),
    path('api/v1/workflows/', include('workflows.api_urls')),
    path('api/v1/equipment/', include('equipment.urls')),
    # 前端路由
    path('', include('core.urls')),
]

# Serve media files in development (only when using local storage)
# 使用更简单的条件判断：只要配置了MEDIA_URL且非空
if settings.MEDIA_URL and settings.MEDIA_ROOT and str(settings.MEDIA_ROOT):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.STATIC_ROOT:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'FAI质量评审系统'
admin.site.site_title = 'FAI系统管理'
admin.site.index_title = '系统管理'
