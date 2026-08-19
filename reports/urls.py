"""
报告前端URL配置
"""
from django.urls import path
from .views import (
    ReportListView, ReportDetailView,
    ReportCreateView, ReportUpdateView, ReportDeleteView,
    ReportGenerateView, ReportDownloadView, ReportPublishView
)

urlpatterns = [
    path('list/', ReportListView.as_view(), name='report_list'),
    path('create/', ReportCreateView.as_view(), name='report_create'),
    path('<uuid:pk>/', ReportDetailView.as_view(), name='report_detail'),
    path('<uuid:pk>/edit/', ReportUpdateView.as_view(), name='report_edit'),
    path('<uuid:pk>/delete/', ReportDeleteView.as_view(), name='report_delete'),
    path('<uuid:pk>/generate/', ReportGenerateView.as_view(), name='report_generate'),
    path('<uuid:pk>/download/', ReportDownloadView.as_view(), name='report_download'),
    path('<uuid:pk>/publish/', ReportPublishView.as_view(), name='report_publish'),
]
