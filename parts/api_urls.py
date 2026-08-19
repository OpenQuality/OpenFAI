"""
零件管理API URL配置
用于 /api/v1/parts/ 路由
"""
from django.urls import path, include
from core.routers import DefaultRouter
from .views import (
    PartViewSet, CADExtractionViewSet, DimensionViewSet,
    DimensionTemplateViewSet, ControlRequirementViewSet,
    RiskPointViewSet, SOPDocumentViewSet, Model3DAnalysisViewSet,
    DrawingReviewViewSet, SurfaceZoneViewSet, StandardInterpretationViewSet,
    InspectionSOPItemViewSet, PartAttachmentViewSet
)

# API视图集路由
router = DefaultRouter()
# 注意：不要用 r'' 作为basename，这会导致所有子路由都被匹配
router.register(r'parts', PartViewSet, basename='part')
router.register(r'attachments', PartAttachmentViewSet, basename='attachment')
router.register(r'extractions', CADExtractionViewSet, basename='extraction')
router.register(r'dimensions', DimensionViewSet, basename='dimension')
router.register(r'templates', DimensionTemplateViewSet, basename='dimension-template')
router.register(r'control-requirements', ControlRequirementViewSet, basename='control-requirement')
router.register(r'risk-points', RiskPointViewSet, basename='risk-point')
router.register(r'sop-documents', SOPDocumentViewSet, basename='sop-document')
router.register(r'model-3d-analyses', Model3DAnalysisViewSet, basename='model-3d-analysis')
router.register(r'drawing-reviews', DrawingReviewViewSet, basename='drawing-review')
router.register(r'surface-zones', SurfaceZoneViewSet, basename='surface-zone')
router.register(r'standard-interpretations', StandardInterpretationViewSet, basename='standard-interpretation')
router.register(r'inspection-sop-items', InspectionSOPItemViewSet, basename='inspection-sop-item')

urlpatterns = [
    # 视图集路由
    path('', include(router.urls)),
    # 兼容旧路由：/api/v1/parts/ 直接访问零件列表
    path('list/', PartViewSet.as_view({'get': 'list', 'post': 'create'}), name='part-list-direct'),
    # 通过文件URL进行OCR识别
    path('ocr/', PartViewSet.as_view({'post': 'ocr'}), name='part-ocr'),
    # OCR模型列表（兼容前端直接调用 /api/v1/parts/ocr_models/）
    path('ocr_models/', PartViewSet.as_view({'get': 'ocr_models'}), name='part-ocr-models'),
]
