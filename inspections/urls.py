from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InspectionPlanViewSet, InspectionCharacteristicViewSet,
    CharacteristicCategoryViewSet,
    InspectionPlanListView, InspectionPlanDetailView, 
    InspectionPlanCreateView, InspectionPlanUpdateView, InspectionPlanDeleteView
)

router = DefaultRouter()
router.register(r'plans', InspectionPlanViewSet)
router.register(r'characteristics', InspectionCharacteristicViewSet)
router.register(r'categories', CharacteristicCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('list/', InspectionPlanListView.as_view(), name='plan_list'),
    path('create/', InspectionPlanCreateView.as_view(), name='plan_create'),
    path('<uuid:pk>/', InspectionPlanDetailView.as_view(), name='plan_detail'),
    path('<uuid:pk>/edit/', InspectionPlanUpdateView.as_view(), name='plan_edit'),
    path('<uuid:pk>/delete/', InspectionPlanDeleteView.as_view(), name='plan_delete'),
]
