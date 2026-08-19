"""
账户应用API URL配置
用于 /api/v1/accounts/ 路由
"""
from django.urls import path, include
from core.routers import DefaultRouter
from .views import (
    UserViewSet, UserProfileViewSet, RoleViewSet, DepartmentViewSet,
    assign_roles, update_profile, approve_user, debug_auth,
)

# API视图集路由
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', UserProfileViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'departments', DepartmentViewSet)

urlpatterns = [
    # 视图集路由
    path('', include(router.urls)),
    
    # 自定义API端点
    path('users/<int:user_id>/assign-roles/', assign_roles, name='api_assign_roles'),
    path('users/<int:user_id>/update-profile/', update_profile, name='api_update_profile'),
    path('users/<int:user_id>/approve/', approve_user, name='api_approve_user'),
    
    # 调试端点
    path('debug-auth/', debug_auth, name='api_debug_auth'),
]
