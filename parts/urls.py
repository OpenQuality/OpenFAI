"""
零件管理前端URL配置
用于前端页面路由
"""
from django.urls import path
from . import views

urlpatterns = [
    # 零件管理前端页面
    path('list/', views.PartListView.as_view(), name='part_list'),
    path('create/', views.PartCreateView.as_view(), name='part_create'),
    path('<uuid:pk>/', views.PartDetailView.as_view(), name='part_detail'),
    path('<uuid:pk>/edit/', views.PartUpdateView.as_view(), name='part_edit'),
    path('<uuid:pk>/delete/', views.PartDeleteView.as_view(), name='part_delete'),
    path('<uuid:pk>/ocr/', views.DrawingOCRView.as_view(), name='drawing_ocr'),
    path('<uuid:pk>/analysis/', views.PartDetailView.as_view(template_name='parts/part_analysis.html'), name='part_analysis'),
    
    # SOP文档管理
    path('sop/', views.SOPListView.as_view(), name='sop_list'),
    path('sop/create/', views.SOPCreateView.as_view(), name='sop_create'),
    path('sop/<int:pk>/', views.SOPDetailView.as_view(), name='sop_detail'),
    path('sop/<int:pk>/edit/', views.SOPUpdateView.as_view(), name='sop_edit'),
    
    # 控制要求管理
    path('control-requirements/', views.ControlRequirementListView.as_view(), name='control_requirement_list'),
    path('control-requirements/create/', views.ControlRequirementCreateView.as_view(), name='control_requirement_create'),
    path('control-requirements/<int:pk>/', views.ControlRequirementDetailView.as_view(), name='control_requirement_detail'),
    path('control-requirements/<int:pk>/edit/', views.ControlRequirementUpdateView.as_view(), name='control_requirement_edit'),
    
    # 风险点管理
    path('risk-points/', views.RiskPointListView.as_view(), name='risk_point_list'),
    path('risk-points/create/', views.RiskPointCreateView.as_view(), name='risk_point_create'),
    path('risk-points/<int:pk>/', views.RiskPointDetailView.as_view(), name='risk_point_detail'),
    path('risk-points/<int:pk>/edit/', views.RiskPointUpdateView.as_view(), name='risk_point_edit'),
]
