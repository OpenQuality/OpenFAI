"""
账户应用URL配置
前端路由和API路由分离
"""
from django.urls import path
from .views import (
    # API视图
    UserViewSet, UserProfileViewSet, RoleViewSet, DepartmentViewSet,
    api_login, api_logout, get_csrf_token, debug_auth,
    assign_roles, update_profile,
    # 前端视图
    login_view, logout_view, ProfileView,
    UserListView, UserDetailView, UserUpdateView,
    RoleListView, RoleUpdateView,
)


# 前端页面路由（在 /accounts/ 下）
urlpatterns = [
    # 登录/登出
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # 用户管理
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:user_id>/assign-roles/', assign_roles, name='assign_roles'),
    
    # 角色管理
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('roles/<int:pk>/edit/', RoleUpdateView.as_view(), name='role_edit'),
    
    # API接口（在 /accounts/ 下的API）
    path('api-auth/', api_login, name='api_login'),
    path('api-logout/', api_logout, name='api_logout'),
    path('api-csrf/', get_csrf_token, name='get_csrf'),
    path('debug-auth/', debug_auth, name='debug_auth'),
]
