from django.urls import path, include
from django.views.generic import TemplateView
from .views import (
    DashboardView, index, StatisticsView, HelpGuideView,
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView,
    ProjectStepUpdateView, OCREngineConfigView, ocr_engine_status, install_ocr_engine,
    system_config_view, ai_vision_config, ai_vision_test, storage_config, storage_test, ocr_status,
    baidu_ocr_config, baidu_ocr_test
)
from inspections.views import (
    InspectionPlanListView, InspectionPlanDetailView, InspectionPlanCreateView, 
    InspectionPlanUpdateView, InspectionPlanDeleteView
)
from equipment.views import EquipmentListView, EquipmentDetailView
from reports.views import (
    ReportListView, ReportDetailView, ReportCreateView, ReportUpdateView, ReportDeleteView,
    ReportGenerateView, ReportDownloadView, ReportPublishView
)
from measurements.views import (
    MeasurementBatchListView, MeasurementBatchDetailView, CpkAnalysisView,
    MeasurementBatchCreateView, MeasurementBatchUpdateView, MeasurementBatchDeleteView,
)

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('about/', TemplateView.as_view(template_name='core/about.html'), name='about'),
    path('help/', HelpGuideView.as_view(), name='help_guide'),
    
    # 用户管理
    path('accounts/', include('accounts.urls')),
    
    # 零件管理前端页面
    path('parts/', include('parts.urls')),
    
    # 设备管理前端页面
    path('equipment/', EquipmentListView.as_view(), name='equipment_list'),
    path('equipment/<uuid:pk>/', EquipmentDetailView.as_view(), name='equipment_detail'),
    
    # 报告管理前端页面
    path('reports/', include('reports.urls')),

    # 审批工作流/不合格品处理前端页面
    path('workflows/', include('workflows.urls')),
    
    # 项目管理
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('projects/create/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<uuid:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<uuid:pk>/edit/', ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<uuid:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/steps/<uuid:pk>/update/', ProjectStepUpdateView.as_view(), name='project_step_update'),
    
    # 检验计划管理 - 使用与模板一致的URL名称
    path('inspections/', InspectionPlanListView.as_view(), name='plan_list'),
    path('inspections/create/', InspectionPlanCreateView.as_view(), name='plan_create'),
    path('inspections/<uuid:pk>/', InspectionPlanDetailView.as_view(), name='plan_detail'),
    path('inspections/<uuid:pk>/edit/', InspectionPlanUpdateView.as_view(), name='plan_edit'),
    path('inspections/<uuid:pk>/delete/', InspectionPlanDeleteView.as_view(), name='plan_delete'),
    
    # 测量批次和Cp/Cpk分析
    path('measurements/', MeasurementBatchListView.as_view(), name='batch_list'),
    path('measurements/create/', MeasurementBatchCreateView.as_view(), name='batch_create'),
    path('measurements/cpk-analysis/', CpkAnalysisView.as_view(), name='cpk_analysis'),
    path('measurements/<uuid:pk>/', MeasurementBatchDetailView.as_view(), name='batch_detail'),
    path('measurements/<uuid:pk>/edit/', MeasurementBatchUpdateView.as_view(), name='batch_edit'),
    path('measurements/<uuid:pk>/delete/', MeasurementBatchDeleteView.as_view(), name='batch_delete'),
    
    # 系统设置
    path('settings/ocr-engines/', OCREngineConfigView.as_view(), name='ocr_engines'),
    
    # API接口
    path('api/v1/settings/ocr-engines/status/', ocr_engine_status, name='api_ocr_engine_status'),
    path('api/v1/settings/ocr-engines/install/', install_ocr_engine, name='api_ocr_engine_install'),
    path('api/v1/settings/config/', system_config_view, name='api_system_config'),
    path('api/v1/settings/config/<str:key>/', system_config_view, name='api_system_config_detail'),
    path('api/v1/settings/ai-vision/', ai_vision_config, name='api_ai_vision_config'),
    path('api/v1/settings/ai-vision/test/', ai_vision_test, name='api_ai_vision_test'),
    path('api/v1/settings/storage/', storage_config, name='api_storage_config'),
    path('api/v1/settings/storage/test/', storage_test, name='api_storage_test'),
    path('api/v1/ocr/status/', ocr_status, name='api_ocr_status'),
    path('api/v1/settings/baidu-ocr/', baidu_ocr_config, name='api_baidu_ocr_config'),
    path('api/v1/settings/baidu-ocr/test/', baidu_ocr_test, name='api_baidu_ocr_test'),
]
