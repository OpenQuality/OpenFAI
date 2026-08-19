"""
工作流API URL配置
用于 /api/v1/workflows/ 路由
"""
from django.urls import path, include
from core.routers import DefaultRouter
from .views import (
    ApprovalWorkflowViewSet, ApprovalStepViewSet,
    NonConformanceReportViewSet, NonConformanceActionViewSet,
)

router = DefaultRouter()
router.register(r'workflows', ApprovalWorkflowViewSet)
router.register(r'steps', ApprovalStepViewSet)
router.register(r'ncr-reports', NonConformanceReportViewSet)
router.register(r'ncr-actions', NonConformanceActionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
