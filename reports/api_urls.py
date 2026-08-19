"""
报告API URL配置
用于 /api/v1/reports/ 路由
"""
from django.urls import path, include
from core.routers import DefaultRouter
from .views import (
    ReportTemplateViewSet, InspectionReportViewSet,
    MaterialCertificationViewSet, SpecialProcessRecordViewSet, FunctionalTestRecordViewSet,
)

# API视图集路由
router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet)
router.register(r'material-certifications', MaterialCertificationViewSet)
router.register(r'special-processes', SpecialProcessRecordViewSet)
router.register(r'functional-tests', FunctionalTestRecordViewSet)
router.register(r'', InspectionReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
