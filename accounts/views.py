from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
import logging
from .models import UserProfile, Role, Department, UserActivity
from .serializers import UserSerializer, UserProfileSerializer, RoleSerializer, DepartmentSerializer

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """用户API视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    """用户档案API视图集"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class RoleViewSet(viewsets.ModelViewSet):
    """角色API视图集"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """部门API视图集"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


# API登录视图 - 无需CSRF
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API登录 - 无需CSRF验证，带详细调试日志"""
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    
    logger.info(f"=== API登录尝试 ===")
    logger.info(f"用户名: {username}")
    logger.info(f"密码长度: {len(password) if password else 0}")
    
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        logger.info(f"API登录成功: {user.username}")
        return Response({
            'status': 'success',
            'user': UserSerializer(user).data,
            'session_key': request.session.session_key
        })
    
    logger.warning(f"API登录失败: 用户名或密码错误")
    return Response(
        {'status': 'error', 'message': '用户名或密码错误'}, 
        status=status.HTTP_401_UNAUTHORIZED
    )


# API登出视图
@api_view(['POST'])
@permission_classes([AllowAny])
def api_logout(request):
    """API登出"""
    logout(request)
    return Response({'status': 'success'})


# 获取CSRF Token
@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """获取CSRF Token"""
    return Response({'status': 'success', 'message': 'CSRF cookie set'})


# 调试端点 - 检查登录状态
@api_view(['GET'])
@permission_classes([AllowAny])
def debug_auth(request):
    """调试认证状态 - 显示当前用户和session信息"""
    try:
        user = request.user
        session = request.session
        
        return Response({
            'user': {
                'is_authenticated': user.is_authenticated,
                'username': getattr(user, 'username', None),
                'id': getattr(user, 'id', None),
                'is_superuser': getattr(user, 'is_superuser', None),
                'is_staff': getattr(user, 'is_staff', None),
            },
            'session': {
                'session_key': session.session_key,
                'keys': list(session.keys()) if session.session_key else [],
                'expire_date': str(session.get_expiry_date()) if session.session_key else None,
            },
            'cookies': dict(request.COOKIES),
            'meta': {
                'HTTP_HOST': request.META.get('HTTP_HOST'),
                'HTTP_ORIGIN': request.META.get('HTTP_ORIGIN'),
                'HTTP_REFERER': request.META.get('HTTP_REFERER'),
                'REMOTE_ADDR': request.META.get('REMOTE_ADDR'),
                'SERVER_NAME': request.META.get('SERVER_NAME'),
                'SERVER_PORT': request.META.get('SERVER_PORT'),
                'wsgi.url_scheme': request.META.get('wsgi.url_scheme'),
            }
        })
    except Exception as e:
        # 确保出错时也返回 JSON
        return Response({
            'user': {
                'is_authenticated': False,
                'username': None,
                'id': None,
                'is_superuser': None,
                'is_staff': None,
            },
            'session': {
                'session_key': None,
                'keys': [],
                'expire_date': None,
            },
            'cookies': {},
            'meta': {},
            'error': str(e)
        })


# 前端视图
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    """登录页面 - 禁用CSRF"""
    def get(self, request):
        return render(request, 'accounts/login.html')
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/dashboard/')
        else:
            return render(request, 'accounts/login.html', {'error': '用户名或密码错误'})


class ProfileView(LoginRequiredMixin, TemplateView):
    """个人档案页面"""
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'employee_id': f'EMP{self.request.user.id:05d}', 'department': '质量部', 'status': 'PENDING'}
        )[0]
        return context


@csrf_exempt
def login_view(request):
    """登录视图 - 传统表单提交方式，带详细调试日志"""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        next_url = request.GET.get('next', '/dashboard/')
        
        logger.info(f"=== 登录尝试 ===")
        logger.info(f"用户名: {username}")
        logger.info(f"密码长度: {len(password)}")
        logger.info(f"目标URL: {next_url}")
        logger.info(f"CSRF Token: {request.POST.get('csrfmiddlewaretoken', 'N/A')[:20]}...")
        logger.info(f"Session Key (登录前): {request.session.session_key}")
        
        # 检查用户是否存在
        try:
            user_obj = User.objects.get(username=username)
            logger.info(f"用户存在: {user_obj.username}, 活跃: {user_obj.is_active}")
        except User.DoesNotExist:
            logger.warning(f"用户不存在: {username}")
            return render(request, 'accounts/login.html', {
                'error': f'用户 "{username}" 不存在',
                'username': username
            })
        
        # 尝试验证
        user = authenticate(request, username=username, password=password)
        logger.info(f"认证结果: {user}")
        
        if user:
            # 检查用户是否活跃
            if not user.is_active:
                logger.warning(f"用户已禁用: {user.username}")
                return render(request, 'accounts/login.html', {
                    'error': '您的账号已被禁用，请联系管理员。',
                    'username': username
                })
            
            # 确保用户有 profile
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(
                    user=user,
                    employee_id=f'EMP{user.id:05d}',
                    department='待分配'
                )
                logger.info(f"为用户创建Profile: {user.username}")
            
            login(request, user)
            logger.info(f"登录成功! Session Key (登录后): {request.session.session_key}")
            logger.info(f"用户ID: {user.id}, 超级用户: {user.is_superuser}")
            return redirect(next_url)
        else:
            logger.warning(f"认证失败: 用户名或密码错误")
            return render(request, 'accounts/login.html', {
                'error': '用户名或密码错误，请检查密码是否正确',
                'username': username
            })
    
    # GET 请求 - 显示登录页面
    logger.info(f"显示登录页面, Session Key: {request.session.session_key}")
    return render(request, 'accounts/login.html')


def logout_view(request):
    """登出视图"""
    logout(request)
    return redirect('/')


# 用户管理视图
class UserListView(LoginRequiredMixin, ListView):
    """用户列表页面"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all().select_related('profile').prefetch_related('profile__roles')
        search = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        if status_filter:
            queryset = queryset.filter(profile__status=status_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.filter(is_active=True)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        # 统计待审核用户数量（已移除，保留变量为了兼容）
        context['pending_count'] = 0
        return context


class UserDetailView(LoginRequiredMixin, DetailView):
    """用户详情页面"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(
            user=self.object,
            defaults={'employee_id': f'EMP{self.object.id:05d}', 'department': '待分配'}
        )
        context['profile'] = profile
        context['all_roles'] = Role.objects.filter(is_active=True)
        context['departments'] = Department.objects.filter(is_active=True)
        # 添加用户角色ID列表，用于模板中判断
        context['user_role_ids'] = list(profile.roles.values_list('id', flat=True))
        # 添加状态显示（基于 is_active）
        if self.object.is_active:
            context['status_display'] = '已激活'
        else:
            context['status_display'] = '已停用'
        return context


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """用户编辑页面"""
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['first_name', 'last_name', 'email', 'is_active', 'is_staff']
    
    def get_success_url(self):
        return reverse_lazy('user_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(
            user=self.object,
            defaults={'employee_id': f'EMP{self.object.id:05d}', 'department': '待分配'}
        )
        context['profile'] = profile
        context['all_roles'] = Role.objects.filter(is_active=True)
        context['departments'] = Department.objects.filter(is_active=True)
        # 添加用户角色ID列表，用于模板中判断
        context['user_role_ids'] = list(profile.roles.values_list('id', flat=True))
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # 更新档案信息
        profile, created = UserProfile.objects.get_or_create(
            user=self.object,
            defaults={'employee_id': f'EMP{self.object.id:05d}', 'department': '待分配', 'status': 'PENDING'}
        )
        profile.department = self.request.POST.get('department', profile.department)
        profile.position = self.request.POST.get('position', profile.position)
        profile.phone = self.request.POST.get('phone', profile.phone)
        profile.save()
        
        # 更新角色
        role_ids = self.request.POST.getlist('user_roles')
        profile.roles.set(role_ids)
        
        messages.success(self.request, '用户信息更新成功')
        return response


class RoleListView(LoginRequiredMixin, ListView):
    """角色列表页面"""
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    """角色编辑页面"""
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'code', 'description', 'is_active']
    success_url = reverse_lazy('role_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['module_permissions'] = Role.MODULE_PERMISSIONS
        return context
    
    def form_valid(self, form):
        # 处理权限配置
        import json
        permissions_json = self.request.POST.get('permissions', '{}')
        try:
            form.instance.permissions = json.loads(permissions_json)
        except:
            form.instance.permissions = {}
        
        messages.success(self.request, '角色更新成功')
        return super().form_valid(form)


# API视图：分配角色
@api_view(['POST'])
def assign_roles(request, user_id):
    """为用户分配角色"""
    user = get_object_or_404(User, pk=user_id)
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={'employee_id': f'EMP{user.id:05d}', 'department': '待分配', 'status': 'PENDING'}
    )
    
    role_ids = request.data.get('roles', [])
    profile.roles.set(role_ids)
    
    # 记录活动
    UserActivity.objects.create(
        user=user,
        activity_type='ROLE_ASSIGNED',
        description=f'角色已更新',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return Response({
        'status': 'success',
        'message': '角色分配成功',
        'roles': list(profile.roles.values_list('id', flat=True))
    })


# API视图：更新用户档案
@api_view(['POST'])
def update_profile(request, user_id):
    """更新用户档案"""
    user = get_object_or_404(User, pk=user_id)
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={'employee_id': f'EMP{user.id:05d}', 'department': '待分配', 'status': 'PENDING'}
    )
    
    profile.employee_id = request.data.get('employee_id', profile.employee_id)
    profile.department = request.data.get('department', profile.department)
    profile.position = request.data.get('position', profile.position)
    profile.phone = request.data.get('phone', profile.phone)
    profile.save()
    
    # 更新用户基本信息
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.email = request.data.get('email', user.email)
    user.save()
    
    return Response({
        'status': 'success',
        'message': '档案更新成功'
    })


# API视图：审核用户
@api_view(['POST'])
def approve_user(request, user_id):
    """审核用户 - 简化版：仅激活/禁用用户"""
    if not request.user.is_superuser and not request.user.is_staff:
        return Response({'status': 'error', 'message': '没有审核权限'}, status=status.HTTP_403_FORBIDDEN)
    
    user = get_object_or_404(User, pk=user_id)
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={'employee_id': f'EMP{user.id:05d}', 'department': '待分配'}
    )
    
    action = request.data.get('action')  # approve, suspend
    reason = request.data.get('reason', '')
    
    if action == 'approve':
        # 激活用户账号
        user.is_active = True
        user.save()
        message = '用户已激活'
    elif action == 'suspend':
        # 停用用户账号
        user.is_active = False
        user.save()
        message = '用户已停用'
    else:
        return Response({'status': 'error', 'message': '无效的操作'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 记录活动
    UserActivity.objects.create(
        user=user,
        activity_type=f'USER_{action.upper()}D',
        description=f'用户状态变更: {message}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return Response({
        'status': 'success',
        'message': message,
        'new_status': 'APPROVED' if user.is_active else 'SUSPENDED',
        'new_status_display': '已激活' if user.is_active else '已停用'
    })


# 权限检查装饰器
def has_permission(module, action):
    """权限检查装饰器"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            try:
                profile = request.user.profile
                for role in profile.roles.filter(is_active=True):
                    if role.has_permission(module, action):
                        return view_func(request, *args, **kwargs)
            except:
                pass
            
            messages.error(request, f'您没有 {module}.{action} 权限')
            return redirect('dashboard')
        return wrapper
    return decorator


# 混入类：权限检查
class PermissionRequiredMixin:
    """权限检查混入类"""
    permission_module = None
    permission_action = None
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        if self.permission_module and self.permission_action:
            try:
                profile = request.user.profile
                for role in profile.roles.filter(is_active=True):
                    if role.has_permission(self.permission_module, self.permission_action):
                        return super().dispatch(request, *args, **kwargs)
            except:
                pass
            
            messages.error(request, f'您没有 {self.permission_module}.{self.permission_action} 权限')
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)
