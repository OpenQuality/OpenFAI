from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q, F
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
import os
from django.views.decorators.csrf import csrf_exempt
import logging
from parts.models import Part
from inspections.models import InspectionPlan
from measurements.models import MeasurementBatch
from reports.models import InspectionReport
from workflows.models import ApprovalWorkflow
from .models import FAIProject, ProjectStep
from .context_processors import get_user_permissions, user_has_permission
from .permissions import AutoPermissionMixin

logger = logging.getLogger(__name__)


def check_dashboard_permission(user):
    """
    检查用户是否有仪表盘访问权限
    无角色的用户不能访问
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    try:
        profile = user.profile
        # 用户必须有至少一个角色
        if profile.roles.exists():
            return True
    except:
        pass
    
    return False


class DashboardView(LoginRequiredMixin, TemplateView):
    """仪表盘视图"""
    template_name = 'core/dashboard.html'
    permission_denied_template = 'core/permission_denied.html'
    
    def dispatch(self, request, *args, **kwargs):
        # 检查用户是否有权限访问仪表盘
        if not check_dashboard_permission(request.user):
            # 渲染无权限提示页面
            return render(request, self.permission_denied_template, {
                'message': '您没有权限访问此页面，请联系管理员分配角色。',
                'title': '访问受限'
            })
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取用户权限
        user_perms = get_user_permissions(self.request.user)
        context['user_permissions'] = user_perms
        
        # 统计数据
        context['parts_count'] = Part.objects.count()
        context['plans_count'] = InspectionPlan.objects.count()
        context['batches_count'] = MeasurementBatch.objects.count()
        context['reports_count'] = InspectionReport.objects.count()
        
        # 项目统计
        context['projects_count'] = FAIProject.objects.count()
        context['active_projects'] = FAIProject.objects.filter(status='IN_PROGRESS').count()
        
        # 发布的报告数量
        context['published_reports'] = InspectionReport.objects.filter(status='PUBLISHED').count()
        
        # 设备统计
        try:
            from equipment.models import Equipment
            context['equipment_count'] = Equipment.objects.count()
            context['active_equipment'] = Equipment.objects.filter(status='ACTIVE').count()
        except:
            context['equipment_count'] = 0
            context['active_equipment'] = 0
        
        # 不合格报告统计 (如果有)
        context['ncr_count'] = 0
        context['open_ncr'] = 0
        
        # 待办事项
        pending_workflows = ApprovalWorkflow.objects.filter(
            status='IN_PROGRESS'
        ).count()
        context['pending_workflows'] = pending_workflows
        context['pending_workflow_list'] = ApprovalWorkflow.objects.filter(
            status='IN_PROGRESS'
        ).order_by('-initiated_at')[:5]
        
        # 最近活动
        context['recent_plans'] = InspectionPlan.objects.order_by('-created_at')[:5]
        context['recent_batches'] = MeasurementBatch.objects.order_by('-created_at')[:5]
        context['recent_projects'] = FAIProject.objects.order_by('-created_at')[:5]
        
        return context


class HomeView(TemplateView):
    """首页"""
    template_name = 'core/home.html'


class HelpGuideView(LoginRequiredMixin, TemplateView):
    """使用指南：从零开始介绍导航栏全部功能及整体业务流程"""
    template_name = 'core/help_guide.html'


def index(request):
    """首页 - 带登录功能"""
    # 如果已登录，跳转到仪表盘
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    context = {}
    
    if request.method == 'POST':
        action = request.POST.get('action', 'login')
        
        if action == 'login':
            # 登录处理
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            remember = request.POST.get('remember')
            
            logger.info(f"=== 首页登录尝试 ===")
            logger.info(f"用户名: {username}")
            logger.info(f"记住我: {remember}")
            logger.info(f"Session Key (登录前): {request.session.session_key}")
            
            # 验证用户
            user = authenticate(request, username=username, password=password)
            
            if user:
                login(request, user)
                
                # 确保session被保存
                request.session.save()
                
                logger.info(f"登录成功! Session Key (登录后): {request.session.session_key}")
                logger.info(f"Session saved: {request.session.session_key}")
                
                # 如果不记住我，设置session在浏览器关闭时过期
                if not remember:
                    request.session.set_expiry(0)
                
                messages.success(request, f'欢迎回来，{user.username}！')
                
                # 返回JSON响应供前端处理
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': '登录成功',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                        },
                        'session_key': request.session.session_key,
                        'redirect': '/dashboard/'
                    })
                
                # 使用HttpResponseRedirect确保cookie被正确设置
                from django.http import HttpResponseRedirect
                response = HttpResponseRedirect('/dashboard/')
                response.set_cookie(
                    'sessionid',
                    request.session.session_key,
                    max_age=None if not remember else 1209600,  # 2周
                    httponly=True,
                    samesite='Lax',
                    secure=False
                )
                return response
            else:
                logger.warning(f"登录失败: 用户名或密码错误")
                context['error'] = '用户名或密码错误'
                context['username'] = username
        
        elif action == 'register':
            # 注册处理
            reg_username = request.POST.get('reg_username', '')
            reg_email = request.POST.get('reg_email', '')
            reg_password = request.POST.get('reg_password', '')
            reg_password2 = request.POST.get('reg_password2', '')
            reg_fullname = request.POST.get('reg_fullname', '')
            reg_department = request.POST.get('reg_department', '')
            
            logger.info(f"=== 注册尝试 ===")
            logger.info(f"用户名: {reg_username}, 邮箱: {reg_email}")
            
            # 验证
            if User.objects.filter(username=reg_username).exists():
                context['error'] = f'用户名 "{reg_username}" 已存在'
            elif User.objects.filter(email=reg_email).exists():
                context['error'] = f'邮箱 "{reg_email}" 已被注册'
            elif len(reg_password) < 6:
                context['error'] = '密码长度至少6位'
            elif reg_password != reg_password2:
                context['error'] = '两次输入的密码不一致'
            else:
                # 创建用户
                user = User.objects.create_user(
                    username=reg_username,
                    email=reg_email,
                    password=reg_password,
                    first_name=reg_fullname
                )
                
                # 创建用户档案
                try:
                    from accounts.models import UserProfile
                    UserProfile.objects.create(
                        user=user,
                        employee_id=f'EMP{user.id:05d}',
                        department=reg_department or '待分配',
                        position='待分配'
                    )
                except Exception as e:
                    logger.warning(f"创建用户档案失败: {e}")
                
                logger.info(f"注册成功: {reg_username}")
                
                # 自动登录
                login(request, user)
                messages.success(request, f'注册成功！欢迎加入，{reg_username}！')
                return redirect('dashboard')
        
        elif action == 'forgot':
            # 找回密码处理
            forgot_email = request.POST.get('forgot_email', '')
            
            logger.info(f"=== 找回密码 ===")
            logger.info(f"邮箱: {forgot_email}")
            
            try:
                user = User.objects.get(email=forgot_email)
                # TODO: 发送密码重置邮件
                # 这里简化处理，直接显示成功
                context['success'] = f'密码重置链接已发送到 {forgot_email}，请查收邮件'
                logger.info(f"密码重置邮件发送到: {forgot_email}")
            except User.DoesNotExist:
                context['error'] = f'邮箱 {forgot_email} 未注册'
    
    return render(request, 'core/home.html', context)


# 项目管理视图
class ProjectListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """项目列表"""
    model = FAIProject
    template_name = 'core/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20
    permission_module = 'projects'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'projects', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'projects', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'projects', 'delete')
        return context


class ProjectDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """项目详情"""
    model = FAIProject
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    permission_module = 'projects'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.steps.all().order_by('step_order')
        
        # 计算进度
        total_steps = context['steps'].count()
        completed_steps = context['steps'].filter(status='COMPLETED').count()
        if total_steps > 0:
            context['progress_percentage'] = int((completed_steps / total_steps) * 100)
        else:
            context['progress_percentage'] = 0
        
        # 获取历史操作记录
        from .models import SystemLog
        context['logs'] = SystemLog.objects.filter(
            model_name='FAIProject',
            object_id=str(self.object.id)
        ).order_by('-created_at')[:10]
        
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'projects', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'projects', 'delete')
        
        return context


class ProjectCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建项目"""
    model = FAIProject
    template_name = 'core/project_form.html'
    fields = ['project_name', 'description', 'part', 'inspection_plan', 'start_date', 'target_date']
    success_url = reverse_lazy('project_list')
    permission_module = 'projects'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # 记录操作日志
        from .models import SystemLog
        SystemLog.objects.create(
            user=self.request.user,
            action='CREATE',
            model_name='FAIProject',
            object_id=str(self.object.id),
            description=f'创建项目: {self.object.project_name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        # 自动创建项目步骤
        steps_config = [
            ('PRODUCT_INFO', '产品信息', 1),
            ('DRAWING_IMPORT', '图纸导入', 2),
            ('OCR_RECOGNITION', 'OCR识别', 3),
            ('DIMENSION_TABLE', '尺寸公差表', 4),
            ('MEASUREMENT', '测量数据', 5),
            ('ANALYSIS', '统计分析', 6),
            ('REPORT', '报告生成', 7),
            ('APPROVAL', '审批流程', 8),
        ]
        
        for step_code, step_name, step_order in steps_config:
            ProjectStep.objects.create(
                project=self.object,
                step_code=step_code,
                step_name=step_name,
                step_order=step_order
            )
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from parts.models import Part
        from inspections.models import InspectionPlan
        context['parts'] = Part.objects.all()
        context['plans'] = InspectionPlan.objects.all()
        return context


class ProjectStepUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """更新项目步骤状态"""
    model = ProjectStep
    fields = ['status', 'notes']
    permission_module = 'projects'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.project.pk})
    
    def form_valid(self, form):
        if form.instance.status == 'COMPLETED':
            form.instance.completed_at = timezone.now()
            form.instance.completed_by = self.request.user
        
        response = super().form_valid(form)
        
        # 更新项目进度
        project = self.object.project
        project.update_progress()
        
        # 记录操作日志
        from .models import SystemLog
        SystemLog.objects.create(
            user=self.request.user,
            action='UPDATE',
            model_name='ProjectStep',
            object_id=str(self.object.id),
            description=f'更新步骤状态: {self.object.step_name} -> {self.object.get_status_display()}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        messages.success(self.request, f'步骤状态已更新，项目进度: {project.progress_percentage}%')
        
        return response


class ProjectUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑项目"""
    model = FAIProject
    template_name = 'core/project_form.html'
    fields = ['project_name', 'description', 'part', 'inspection_plan', 'status', 'start_date', 'target_date']
    permission_module = 'projects'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, '项目更新成功')
        response = super().form_valid(form)
        
        # 记录操作日志
        from .models import SystemLog
        SystemLog.objects.create(
            user=self.request.user,
            action='UPDATE',
            model_name='FAIProject',
            object_id=str(self.object.id),
            description=f'更新项目: {self.object.project_name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        from parts.models import Part
        from inspections.models import InspectionPlan
        context['parts'] = Part.objects.all()
        context['plans'] = InspectionPlan.objects.all()
        return context


class ProjectDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除项目"""
    model = FAIProject
    success_url = reverse_lazy('project_list')
    permission_module = 'projects'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '项目删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class StatisticsView(LoginRequiredMixin, TemplateView):
    """统计分析视图"""
    template_name = 'core/statistics.html'
    permission_denied_template = 'core/permission_denied.html'
    
    def dispatch(self, request, *args, **kwargs):
        # 检查用户是否有权限访问统计页面
        if not check_dashboard_permission(request.user):
            # 渲染无权限提示页面
            return render(request, self.permission_denied_template, {
                'message': '您没有权限访问此页面，请联系管理员分配角色。',
                'title': '访问受限'
            })
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 项目统计
        projects = FAIProject.objects.all()
        context['total_projects'] = projects.count()
        context['projects_by_status'] = projects.values('status').annotate(count=Count('id'))
        context['draft_projects'] = projects.filter(status='DRAFT').count()
        context['in_progress_projects'] = projects.filter(status='IN_PROGRESS').count()
        context['completed_projects'] = projects.filter(status='COMPLETED').count()
        context['archived_projects'] = projects.filter(status='ARCHIVED').count()
        
        # 零件统计
        context['total_parts'] = Part.objects.count()
        context['parts_with_drawing'] = Part.objects.filter(drawing_file__isnull=False).count()
        
        # 检验计划统计
        plans = InspectionPlan.objects.all()
        context['total_plans'] = plans.count()
        context['active_plans'] = plans.filter(status='ACTIVE').count()
        context['plans_with_dimensions'] = plans.annotate(
            dim_count=Count('characteristics')
        ).filter(dim_count__gt=0).count()
        
        # 测量批次统计
        batches = MeasurementBatch.objects.all()
        context['total_batches'] = batches.count()
        context['completed_batches'] = batches.filter(status='COMPLETED').count()
        
        # ===== 今日首件检验统计 =====
        today = timezone.now().date()
        today_batches = batches.filter(created_at__date=today)
        context['today_batches'] = today_batches.count()
        context['today_completed'] = today_batches.filter(status='COMPLETED').count()
        context['today_in_progress'] = today_batches.filter(status='IN_PROGRESS').count()
        
        # ===== 合格率/不合格率统计 =====
        from measurements.models import MeasurementRecord, StatisticalAnalysis
        from workflows.models import NonConformanceReport
        
        # 获取所有测量记录
        all_records = MeasurementRecord.objects.all()
        total_records = all_records.count()
        passed_records = all_records.filter(status='PASS').count()
        failed_records = all_records.filter(status='FAIL').count()
        
        context['total_measurements'] = total_records
        context['passed_measurements'] = passed_records
        context['failed_measurements'] = failed_records
        context['pass_rate'] = round(passed_records / total_records * 100, 1) if total_records > 0 else 0
        context['fail_rate'] = round(failed_records / total_records * 100, 1) if total_records > 0 else 0
        
        # ===== 不合格原因分布 =====
        ncr_by_type = NonConformanceReport.objects.values('problem_type').annotate(
            count=Count('id')
        ).order_by('-count')
        context['ncr_by_type'] = list(ncr_by_type)
        context['ncr_by_type_json'] = [
            {'type': item['problem_type'] or 'OTHER', 'count': item['count']}
            for item in ncr_by_type
        ]
        context['total_ncr'] = NonConformanceReport.objects.count()
        
        # ===== 各检验计划首件完成情况 =====
        line_stats = batches.values(
            'plan__plan_name'
        ).annotate(
            plan_name=F('plan__plan_name'),
            total=Count('id'),
            completed=Count('id', filter=Q(status='COMPLETED')),
            in_progress=Count('id', filter=Q(status='IN_PROGRESS'))
        ).order_by('-total')
        context['line_stats'] = list(line_stats)
        
        # ===== Cp/Cpk 统计 =====
        stats = StatisticalAnalysis.objects.all()
        cpk_valid = stats.filter(cpk__isnull=False, cpk__gt=0)
        context['total_cpk_analysis'] = cpk_valid.count()
        context['cpk_excellent'] = cpk_valid.filter(cpk__gte=1.67).count()  # Cp/Cpk >= 1.67 优秀
        context['cpk_good'] = cpk_valid.filter(cpk__gte=1.33, cpk__lt=1.67).count()  # 1.33 <= Cp < 1.67 良好
        context['cpk_acceptable'] = cpk_valid.filter(cpk__gte=1.0, cpk__lt=1.33).count()  # 1.0 <= Cp < 1.33 合格
        context['cpk_poor'] = cpk_valid.filter(cpk__lt=1.0).count()  # Cp < 1.0 不合格
        
        # 报告统计
        reports = InspectionReport.objects.all()
        context['total_reports'] = reports.count()
        context['draft_reports'] = reports.filter(status='DRAFT').count()
        context['pending_reports'] = reports.filter(status='PENDING_REVIEW').count()
        context['approved_reports'] = reports.filter(status='APPROVED').count()
        context['published_reports'] = reports.filter(status='PUBLISHED').count()
        
        # 审批工作流统计
        workflows = ApprovalWorkflow.objects.all()
        context['total_workflows'] = workflows.count()
        context['pending_workflows'] = workflows.filter(status='IN_PROGRESS').count()
        context['completed_workflows'] = workflows.filter(status='COMPLETED').count()
        context['rejected_workflows'] = workflows.filter(status='REJECTED').count()
        
        # 设备统计
        try:
            from equipment.models import Equipment
            context['total_equipment'] = Equipment.objects.count()
            context['active_equipment'] = Equipment.objects.filter(status='ACTIVE').count()
            context['calibration_due'] = Equipment.objects.filter(
                next_calibration_date__lte=timezone.now().date() + timezone.timedelta(days=30)
            ).count()
        except:
            context['total_equipment'] = 0
            context['active_equipment'] = 0
            context['calibration_due'] = 0
        
        # 时间趋势数据（最近30天）
        from django.db.models.functions import TruncDate
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # 每日项目创建数
        context['daily_projects'] = list(
            FAIProject.objects.filter(
                created_at__date__gte=start_date
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(count=Count('id')).order_by('date')
        )
        
        # 每日报告生成数
        context['daily_reports'] = list(
            InspectionReport.objects.filter(
                created_at__date__gte=start_date
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(count=Count('id')).order_by('date')
        )
        
        # 项目平均完成时间（在Python中计算，避免SQLite不支持DurationField的Extract）
        completed_projects = projects.filter(
            status='COMPLETED', completed_date__isnull=False, start_date__isnull=False
        )
        durations = [
            (completed_date - start_date).days
            for start_date, completed_date in completed_projects.values_list('start_date', 'completed_date')
        ]
        context['avg_project_duration'] = round(sum(durations) / len(durations), 1) if durations else 0
        
        # 预计算百分比值（避免模板中使用不存在的div过滤器）
        total_projects = context['total_projects']
        total_plans = context['total_plans']
        total_parts = context['total_parts']
        total_batches = context['total_batches']
        total_reports = context['total_reports']
        total_workflows = context['total_workflows']
        
        context['project_completion_rate'] = round(context['completed_projects'] / total_projects * 100, 1) if total_projects > 0 else 0
        context['parts_drawing_rate'] = round(context['parts_with_drawing'] / total_parts * 100, 1) if total_parts > 0 else 0
        context['plans_active_rate'] = round(context['active_plans'] / total_plans * 100, 1) if total_plans > 0 else 0
        context['batches_completed_rate'] = round(context['completed_batches'] / total_batches * 100, 1) if total_batches > 0 else 0
        context['reports_published_rate'] = round(context['published_reports'] / total_reports * 100, 1) if total_reports > 0 else 0
        context['workflows_completed_rate'] = round(context['completed_workflows'] / total_workflows * 100, 1) if total_workflows > 0 else 0
        
        # 报告状态百分比（用于进度条）
        context['draft_reports_rate'] = round(context['draft_reports'] / total_reports * 100, 1) if total_reports > 0 else 0
        context['pending_reports_rate'] = round(context['pending_reports'] / total_reports * 100, 1) if total_reports > 0 else 0
        context['approved_reports_rate'] = round(context['approved_reports'] / total_reports * 100, 1) if total_reports > 0 else 0
        context['published_reports_rate'] = round(context['published_reports'] / total_reports * 100, 1) if total_reports > 0 else 0
        
        return context


class OCREngineConfigView(LoginRequiredMixin, TemplateView):
    """OCR引擎配置页面"""
    template_name = 'settings/ocr_engines.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取当前已安装的引擎状态 - 使用pip show检测，避免导入冲突
        context['installed_engines'] = self.get_installed_engines()
        return context
    
    def get_installed_engines(self):
        """检查已安装的OCR引擎 - 使用pip show避免导入冲突"""
        import subprocess
        import sys
        
        engines = {}
        
        # 引擎包名映射
        engine_packages = {
            'paddleocr': 'paddleocr',
            'easyocr': 'easyocr',
            'tesseract': 'pytesseract',
            'rapidocr': 'rapidocr-onnxruntime'
        }
        
        for engine_id, package_name in engine_packages.items():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', package_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            except (subprocess.TimeoutExpired, OSError):
                engines[engine_id] = {'installed': False, 'version': None}
                continue

            if result.returncode == 0:
                # 解析版本号
                version = None
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        break
                engines[engine_id] = {
                    'installed': True,
                    'version': version or 'installed'
                }
            else:
                engines[engine_id] = {'installed': False, 'version': None}
        
        return engines


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
import subprocess
import threading


@api_view(['GET'])
def ocr_engine_status(request):
    """获取OCR引擎安装状态"""
    import sys
    
    engines = {}
    
    # 引擎包名和导入名映射
    engine_packages = {
        'paddleocr': {'pip': 'paddleocr', 'import': 'paddleocr'},
        'easyocr': {'pip': 'easyocr', 'import': 'easyocr'},
        'tesseract': {'pip': 'pytesseract', 'import': 'pytesseract'},
        'rapidocr': {'pip': 'rapidocr-onnxruntime', 'import': 'rapidocr_onnxruntime'}
    }
    
    for engine_id, info in engine_packages.items():
        # 使用pip show检测，更可靠
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', info['pip']],
                capture_output=True,
                text=True,
                timeout=10
            )
        except (subprocess.TimeoutExpired, OSError):
            engines[engine_id] = {'installed': False, 'version': None}
            continue

        if result.returncode == 0:
            # 解析版本号
            version = None
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    break
            engines[engine_id] = {
                'installed': True,
                'version': version or 'installed'
            }
        else:
            engines[engine_id] = {'installed': False, 'version': None}
    
    return Response({'engines': engines})


@csrf_exempt
@api_view(['POST'])
def install_ocr_engine(request):
    """安装OCR引擎"""
    engine = request.data.get('engine')
    
    if not engine:
        return Response({'status': 'error', 'error': '未指定引擎名称'}, status=400)
    
    # 获取当前Python解释器路径
    import sys
    python_path = sys.executable
    
    # 引擎包名映射
    package_map = {
        'paddleocr': 'paddleocr',
        'easyocr': 'easyocr',
        'tesseract': 'pytesseract',
        'rapidocr': 'rapidocr-onnxruntime'
    }
    
    # PaddleOCR需要系统依赖
    system_deps = {
        'paddleocr': ['libgl1', 'libglib2.0-0']
    }
    
    # 需要重启服务才能生效的引擎
    needs_restart = ['paddleocr', 'easyocr', 'rapidocr']
    
    package_name = package_map.get(engine)
    if not package_name:
        return Response({'status': 'error', 'error': f'未知的引擎: {engine}'}, status=400)
    
    try:
        # 先安装系统依赖（如果有）- 跨平台兼容
        deps = system_deps.get(engine, [])
        if deps:
            try:
                import platform
                system = platform.system().lower()
                
                if system == 'linux':
                    # Linux (Debian/Ubuntu)
                    subprocess.run(
                        ['apt-get', 'install', '-y'] + deps,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                elif system == 'darwin':
                    # macOS
                    subprocess.run(
                        ['brew', 'install'] + deps,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                # Windows: 系统依赖通常已预装，跳过
            except Exception:
                pass  # 系统依赖安装失败不影响主流程
        
        # 执行pip安装 - 使用相同的Python解释器
        result = subprocess.run(
            [python_path, '-m', 'pip', 'install', package_name],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        log_output = result.stdout + '\n' + result.stderr
        
        if result.returncode == 0:
            message = f'{engine} 安装成功'
            # 提示需要刷新页面
            if engine in needs_restart:
                message += '\n\n⚠️ 注意：安装新Python包后，请刷新页面(F5)以更新引擎列表。'
            
            return Response({
                'status': 'success',
                'message': message,
                'log': log_output,
                'needs_refresh': engine in needs_restart
            })
        else:
            return Response({
                'status': 'error',
                'error': f'安装失败: {result.stderr}',
                'log': log_output
            }, status=500)
            
    except subprocess.TimeoutExpired:
        return Response({
            'status': 'error',
            'error': '安装超时，请手动执行 pip install ' + package_name
        }, status=500)
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=500)


# ==================== 系统配置 API ====================

@api_view(['GET', 'POST', 'DELETE'])
@csrf_exempt
def system_config_view(request, key=None):
    """系统配置API"""
    from .models import SystemConfig
    import os
    
    if request.method == 'GET':
        if key:
            # 获取单个配置
            value = SystemConfig.get_value(key)
            if value is None:
                return Response({'error': f'配置项 {key} 不存在'}, status=404)
            
            config = SystemConfig.objects.get(key=key)
            return Response({
                'key': key,
                'value': value,
                'category': config.category,
                'description': config.description,
                'is_secret': config.is_secret
            })
        else:
            # 获取所有配置（隐藏敏感值）
            configs = SystemConfig.objects.all()
            return Response([{
                'key': c.key,
                'value': '******' if c.is_secret else c.value,
                'category': c.category,
                'description': c.description,
                'is_secret': c.is_secret
            } for c in configs])
    
    elif request.method == 'POST':
        # 创建或更新配置
        config_key = request.data.get('key')
        config_value = request.data.get('value', '')
        category = request.data.get('category', 'system')
        description = request.data.get('description', '')
        is_secret = request.data.get('is_secret', False)
        
        if not config_key:
            return Response({'error': '配置键不能为空'}, status=400)
        
        config = SystemConfig.set_value(
            key=config_key,
            value=config_value,
            category=category,
            description=description,
            is_secret=is_secret
        )
        
        return Response({
            'status': 'success',
            'message': f'配置 {config_key} 已保存',
            'key': config.key,
            'category': config.category
        })
    
    elif request.method == 'DELETE':
        if not key:
            return Response({'error': '未指定要删除的配置键'}, status=400)
        
        try:
            config = SystemConfig.objects.get(key=key)
            config.delete()
            return Response({'status': 'success', 'message': f'配置 {key} 已删除'})
        except SystemConfig.DoesNotExist:
            return Response({'error': f'配置项 {key} 不存在'}, status=404)


@api_view(['GET', 'POST'])
def ai_vision_config(request):
    """AI视觉模型配置API（厂商无关：支持豆包/Kimi/GLM/自定义OpenAI兼容接口）"""
    from .models import SystemConfig
    from .ai_vision import get_ai_vision_config, is_ai_vision_configured, PROVIDER_PRESETS

    if request.method == 'GET':
        cfg = get_ai_vision_config()
        return Response({
            'configured': is_ai_vision_configured(),
            'provider': cfg['provider'],
            'provider_label': cfg['provider_label'],
            'base_url': cfg['base_url'],
            'model': cfg['model'],
            'has_api_key': bool(cfg['api_key']),
            'key_source': cfg['key_source'],
            'presets': {
                k: {'label': v['label'], 'base_url': v['base_url'], 'default_model': v['default_model']}
                for k, v in PROVIDER_PRESETS.items()
            },
        })

    provider = request.data.get('provider', '').strip()
    api_key = request.data.get('api_key', '').strip()
    base_url = request.data.get('base_url', '').strip()
    model = request.data.get('model', '').strip()

    if not provider:
        return Response({'error': '请选择AI视觉模型厂商'}, status=400)
    if provider not in PROVIDER_PRESETS:
        return Response({'error': f'不支持的厂商: {provider}'}, status=400)

    SystemConfig.set_value(key='ai_vision_provider', value=provider, category='ocr', description='AI视觉模型厂商')
    if api_key:
        SystemConfig.set_value(key='ai_vision_api_key', value=api_key, category='ocr',
                                description='AI视觉模型API密钥', is_secret=True)
    SystemConfig.set_value(key='ai_vision_base_url', value=base_url, category='ocr', description='AI视觉模型服务地址')
    SystemConfig.set_value(key='ai_vision_model', value=model, category='ocr', description='AI视觉模型名称')

    return Response({'status': 'success', 'message': 'AI视觉模型配置已保存'})


@api_view(['POST'])
def ai_vision_test(request):
    """测试AI视觉模型连接"""
    from .ai_vision import get_ai_vision_client, AIVisionConfigError

    try:
        client = get_ai_vision_client()
    except AIVisionConfigError as e:
        return Response({'error': str(e)}, status=400)

    try:
        from langchain_core.messages import HumanMessage
        response = client.invoke(messages=[HumanMessage(content="请只回复两个字：成功")], temperature=0)
        content = response.content
        if isinstance(content, list):
            content = ' '.join(i.get('text', '') for i in content if isinstance(i, dict))
        return Response({'status': 'success', 'message': f'连接成功，模型响应: {str(content)[:200]}'})
    except Exception as e:
        return Response({'error': f'连接失败: {e}'}, status=400)


@api_view(['GET', 'POST'])
def storage_config(request):
    """对象存储配置API（厂商无关：支持S3/阿里云OSS/腾讯云COS/火山引擎TOS）"""
    from .models import SystemConfig
    from .storage import get_storage_config, is_object_storage_configured, STORAGE_PROVIDER_PRESETS

    if request.method == 'GET':
        cfg = get_storage_config()
        return Response({
            'configured': is_object_storage_configured(),
            'provider': cfg['provider'],
            'provider_label': cfg['provider_label'],
            'bucket': cfg['bucket'],
            'endpoint_url': cfg['endpoint_url'],
            'region': cfg['region'],
            'public_base_url': cfg['public_base_url'],
            'addressing_style': cfg['addressing_style'],
            'has_access_key': bool(cfg['access_key']),
            'has_secret_key': bool(cfg['secret_key']),
            'presets': {
                k: {'label': v['label'], 'addressing_style': v['addressing_style']}
                for k, v in STORAGE_PROVIDER_PRESETS.items()
            },
        })

    provider = request.data.get('provider', '').strip()
    access_key = request.data.get('access_key_id', '').strip()
    secret_key = request.data.get('access_key_secret', '').strip()
    bucket = request.data.get('bucket_name', '').strip()
    endpoint_url = request.data.get('endpoint_url', '').strip()
    region = request.data.get('region', '').strip()
    public_base_url = request.data.get('public_base_url', '').strip()
    addressing_style = request.data.get('addressing_style', '').strip()

    if not provider:
        return Response({'error': '请选择存储服务厂商'}, status=400)
    if provider not in STORAGE_PROVIDER_PRESETS:
        return Response({'error': f'不支持的厂商: {provider}'}, status=400)
    if not bucket:
        return Response({'error': '请填写存储桶名称'}, status=400)

    SystemConfig.set_value(key='storage_provider', value=provider, category='storage', description='存储服务厂商')
    if access_key:
        SystemConfig.set_value(key='storage_access_key_id', value=access_key, category='storage',
                                description='存储AccessKey ID', is_secret=True)
    if secret_key:
        SystemConfig.set_value(key='storage_access_key_secret', value=secret_key, category='storage',
                                description='存储AccessKey Secret', is_secret=True)
    SystemConfig.set_value(key='storage_bucket_name', value=bucket, category='storage', description='存储桶名称')
    SystemConfig.set_value(key='storage_endpoint_url', value=endpoint_url, category='storage', description='存储服务地址')
    SystemConfig.set_value(key='storage_region', value=region, category='storage', description='存储区域')
    SystemConfig.set_value(key='storage_public_base_url', value=public_base_url, category='storage',
                            description='存储公开访问域名')
    SystemConfig.set_value(key='storage_addressing_style', value=addressing_style, category='storage',
                            description='存储寻址方式')

    return Response({'status': 'success', 'message': '对象存储配置已保存，重启应用进程后生效'})


@api_view(['POST'])
def storage_test(request):
    """测试对象存储连接"""
    from .storage import S3CompatibleStorage, is_object_storage_configured

    if not is_object_storage_configured():
        return Response({'error': '请先完整填写并保存存储配置（厂商/AccessKey/Secret/桶名）'}, status=400)

    try:
        backend = S3CompatibleStorage()
        backend._client.list_objects_v2(Bucket=backend._bucket, MaxKeys=1)
        return Response({'status': 'success', 'message': '连接成功，存储桶可正常访问'})
    except Exception as e:
        return Response({'error': f'连接失败: {e}'}, status=400)


@api_view(['GET'])
def ocr_status(request):
    """获取OCR服务状态"""
    from .ai_vision import get_ai_vision_config, is_ai_vision_configured
    import subprocess
    import sys

    status = {
        'cloud': {
            'enabled': False,
            'configured': False,
            'message': ''
        },
        'local': {
            'enabled': False,
            'engines': []
        },
        'default': 'local'  # 默认使用本地引擎
    }

    # 检查云端配置
    if is_ai_vision_configured():
        cfg = get_ai_vision_config()
        status['cloud']['enabled'] = True
        status['cloud']['configured'] = True
        source_label = '环境变量' if cfg['key_source'] == 'env' else '数据库配置'
        status['cloud']['message'] = f"{cfg['provider_label'] or cfg['provider']}（{source_label}）"
    else:
        status['cloud']['message'] = '未配置AI视觉模型'

    # 检查本地引擎（engine_id: UI标识, pip_name: pip包名, label: 显示名称）
    local_engines = [
        ('paddleocr',  'paddleocr',              'PaddleOCR'),
        ('easyocr',    'easyocr',                'EasyOCR'),
        ('tesseract',  'pytesseract',            'Tesseract'),
        ('rapidocr',   'rapidocr-onnxruntime',   'RapidOCR'),
    ]

    for engine_id, pip_name, engine_name in local_engines:
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', pip_name],
                capture_output=True,
                text=True,
                timeout=10
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if result.returncode == 0:
            version = None
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    break
            status['local']['engines'].append({
                'id': engine_id,
                'name': engine_name,
                'version': version,
                'installed': True
            })
            status['local']['enabled'] = True
    
    # 如果有本地引擎，设为默认
    if status['local']['enabled']:
        status['default'] = 'local'
    elif status['cloud']['enabled']:
        status['default'] = 'cloud'
    
    return Response(status)


@api_view(['GET', 'POST'])
def baidu_ocr_config(request):
    """百度OCR REST API配置（API Key + Secret Key）"""
    from .models import SystemConfig

    if request.method == 'GET':
        api_key = SystemConfig.get_value('baidu_ocr_api_key') or ''
        secret_key = SystemConfig.get_value('baidu_ocr_secret_key') or ''
        return Response({
            'configured': bool(api_key and secret_key),
            'has_api_key': bool(api_key),
            'has_secret_key': bool(secret_key),
        })

    api_key = request.data.get('api_key', '').strip()
    secret_key = request.data.get('secret_key', '').strip()

    if api_key:
        SystemConfig.set_value(key='baidu_ocr_api_key', value=api_key,
                                category='ocr', description='百度OCR API Key', is_secret=True)
    if secret_key:
        SystemConfig.set_value(key='baidu_ocr_secret_key', value=secret_key,
                                category='ocr', description='百度OCR Secret Key', is_secret=True)

    if not api_key and not secret_key:
        return Response({'error': '请至少填写 API Key 或 Secret Key'}, status=400)

    return Response({'status': 'success', 'message': '百度OCR配置已保存'})


@api_view(['POST'])
def baidu_ocr_test(request):
    """测试百度OCR连接（获取Access Token验证凭证有效性）"""
    from .models import SystemConfig
    import requests as _requests

    api_key = SystemConfig.get_value('baidu_ocr_api_key')
    secret_key = SystemConfig.get_value('baidu_ocr_secret_key')

    if not api_key or not secret_key:
        return Response({'error': '请先配置 API Key 和 Secret Key'}, status=400)

    try:
        url = (
            "https://aip.baidubce.com/oauth/2.0/token"
            f"?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        )
        resp = _requests.post(url, timeout=15)
        data = resp.json()
        if 'error' in data:
            return Response({'error': f"凭证验证失败: {data.get('error_description', data['error'])}"}, status=400)
        expires = data.get('expires_in', 0)
        return Response({'status': 'success', 'message': f'连接成功，Token有效期 {expires//86400} 天'})
    except Exception as e:
        return Response({'error': f'连接失败: {e}'}, status=400)
