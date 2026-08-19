from django.urls import path, include
from core.routers import DefaultRouter  # 使用自定义Router兼容Django 6.0
from . import views

router = DefaultRouter()
router.register(r'batches', views.MeasurementBatchViewSet)
router.register(r'records', views.MeasurementRecordViewSet)
router.register(r'statistics', views.StatisticalAnalysisViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('list/', views.MeasurementBatchListView.as_view(), name='batch_list'),
    path('create/', views.MeasurementBatchCreateView.as_view(), name='batch_create'),
    path('<uuid:pk>/', views.MeasurementBatchDetailView.as_view(), name='batch_detail'),
    path('<uuid:pk>/edit/', views.MeasurementBatchUpdateView.as_view(), name='batch_edit'),
    path('<uuid:pk>/delete/', views.MeasurementBatchDeleteView.as_view(), name='batch_delete'),
    # Cp/Cpk分析页面
    path('cpk-analysis/', views.CpkAnalysisView.as_view(), name='cpk_analysis'),
]
