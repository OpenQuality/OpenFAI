"""
工作流前端URL配置
用于前端页面路由
"""
from django.urls import path
from .views import (
    WorkflowListView, WorkflowDetailView, WorkflowCreateView, WorkflowUpdateView, WorkflowDeleteView,
    NonConformanceListView, NonConformanceDetailView,
    NonConformanceCreateView, NonConformanceUpdateView, NonConformanceDeleteView
)

urlpatterns = [
    path('list/', WorkflowListView.as_view(), name='workflow_list'),
    path('create/', WorkflowCreateView.as_view(), name='workflow_create'),
    path('<uuid:pk>/', WorkflowDetailView.as_view(), name='workflow_detail'),
    path('<uuid:pk>/edit/', WorkflowUpdateView.as_view(), name='workflow_edit'),
    path('<uuid:pk>/delete/', WorkflowDeleteView.as_view(), name='workflow_delete'),

    # 不合格品处理
    path('ncr/', NonConformanceListView.as_view(), name='ncr_list'),
    path('ncr/create/', NonConformanceCreateView.as_view(), name='ncr_create'),
    path('ncr/<uuid:pk>/', NonConformanceDetailView.as_view(), name='ncr_detail'),
    path('ncr/<uuid:pk>/edit/', NonConformanceUpdateView.as_view(), name='ncr_edit'),
    path('ncr/<uuid:pk>/delete/', NonConformanceDeleteView.as_view(), name='ncr_delete'),
]
