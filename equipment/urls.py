from django.urls import path, include
from core.routers import DefaultRouter  # 使用自定义Router兼容Django 6.0
from .views import (
    EquipmentViewSet, EquipmentConnectionViewSet,
    MeasurementDataImportViewSet,
    EquipmentListView, EquipmentDetailView
)

router = DefaultRouter()
router.register(r'', EquipmentViewSet)
router.register(r'connections', EquipmentConnectionViewSet)
router.register(r'imports', MeasurementDataImportViewSet)

urlpatterns = [
    # API路由
    path('', include(router.urls)),
]
