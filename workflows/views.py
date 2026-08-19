from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from .models import (
    ApprovalWorkflow, ApprovalStep, ElectronicSignature,
    NonConformanceReport, NonConformanceAction
)
from .serializers import (
    ApprovalWorkflowSerializer, ApprovalWorkflowDetailSerializer, ApprovalStepSerializer,
    NonConformanceReportSerializer, NonConformanceActionSerializer,
)
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """审批工作流API视图集"""
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = ApprovalWorkflowSerializer
    filterset_fields = ['workflow_type', 'status', 'initiated_by']
    ordering_fields = ['initiated_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ApprovalWorkflowDetailSerializer
        return ApprovalWorkflowSerializer
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批通过"""
        workflow = self.get_object()
        comments = request.data.get('comments', '')
        signature_image = request.FILES.get('signature_image')
        
        # 获取当前步骤
        current_step = workflow.current_step_info
        if not current_step:
            return Response(
                {'error': '没有找到当前审批步骤'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if current_step.status != 'PENDING':
            return Response(
                {'error': '该步骤已处理'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 更新步骤状态
        current_step.status = 'APPROVED'
        current_step.approved_at = timezone.now()
        current_step.comments = comments
        current_step.save()
        
        # 创建电子签名
        ElectronicSignature.objects.create(
            step=current_step,
            user=request.user,
            signature_image=signature_image,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # 检查是否还有下一步
        next_step = workflow.steps.filter(
            step_number=workflow.current_step + 1
        ).first()
        
        if next_step:
            workflow.current_step += 1
            workflow.status = 'IN_PROGRESS'
        else:
            workflow.status = 'COMPLETED'
            workflow.completed_at = timezone.now()
            
            # 更新关联对象状态
            if workflow.plan:
                workflow.plan.status = 'ACTIVE'
                workflow.plan.approved_by = request.user
                workflow.plan.approved_at = timezone.now()
                workflow.plan.save()
            elif workflow.report:
                workflow.report.status = 'PUBLISHED'
                workflow.report.published_by = request.user
                workflow.report.published_at = timezone.now()
                workflow.report.save()
        
        workflow.save()
        
        return Response({
            'status': 'success',
            'message': '审批通过',
            'workflow_status': workflow.status
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """审批拒绝"""
        workflow = self.get_object()
        comments = request.data.get('comments', '')
        
        if not comments:
            return Response(
                {'error': '拒绝时必须填写意见'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_step = workflow.current_step_info
        if not current_step or current_step.status != 'PENDING':
            return Response(
                {'error': '无法拒绝'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_step.status = 'REJECTED'
        current_step.approved_at = timezone.now()
        current_step.comments = comments
        current_step.save()
        
        workflow.status = 'REJECTED'
        workflow.completed_at = timezone.now()
        workflow.save()
        
        return Response({
            'status': 'success',
            'message': '审批已拒绝'
        })
    
    @action(detail=False, methods=['get'])
    def my_pending(self, request):
        """我的待审批"""
        pending_workflows = ApprovalWorkflow.objects.filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            steps__approver=request.user,
            steps__status='PENDING'
        ).distinct()
        
        serializer = self.get_serializer(pending_workflows, many=True)
        return Response(serializer.data)


class ApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """审批步骤API视图集"""
    queryset = ApprovalStep.objects.all()
    serializer_class = ApprovalStepSerializer
    filterset_fields = ['workflow', 'status', 'approver']


class NonConformanceReportViewSet(viewsets.ModelViewSet):
    """不合格品报告API视图集"""
    queryset = NonConformanceReport.objects.all()
    serializer_class = NonConformanceReportSerializer
    filterset_fields = ['status', 'problem_type', 'part']

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """更新不合格品报告状态"""
        ncr = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = dict(NonConformanceReport.STATUS_CHOICES)
        if new_status not in valid_statuses:
            return Response({'error': '无效的状态值'}, status=status.HTTP_400_BAD_REQUEST)
        ncr.status = new_status
        ncr.save(update_fields=['status', 'updated_at'])
        return Response(NonConformanceReportSerializer(ncr).data)


class NonConformanceActionViewSet(viewsets.ModelViewSet):
    """不合格品处理措施API视图集"""
    queryset = NonConformanceAction.objects.all()
    serializer_class = NonConformanceActionSerializer
    filterset_fields = ['ncr', 'status', 'action_type']


# 前端视图
class WorkflowListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """工作流列表页面"""
    model = ApprovalWorkflow
    template_name = 'workflows/workflow_list.html'
    context_object_name = 'workflows'
    paginate_by = 20
    permission_module = 'workflows'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'workflows', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'workflows', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'workflows', 'delete')
        context['can_approve'] = user_has_permission(self.request.user, 'workflows', 'approve')
        return context


class WorkflowDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """工作流详情页面"""
    model = ApprovalWorkflow
    template_name = 'workflows/workflow_detail.html'
    context_object_name = 'workflow'
    permission_module = 'workflows'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.steps.all()
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_approve'] = user_has_permission(self.request.user, 'workflows', 'approve')
        context['can_reject'] = user_has_permission(self.request.user, 'workflows', 'reject')
        return context


class WorkflowCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建审批工作流"""
    model = ApprovalWorkflow
    template_name = 'workflows/workflow_form.html'
    fields = ['workflow_type', 'plan', 'report', 'notes']
    success_url = reverse_lazy('workflow_list')
    permission_module = 'workflows'
    
    def form_valid(self, form):
        form.instance.initiated_by = self.request.user
        form.instance.status = 'PENDING'
        response = super().form_valid(form)
        
        # 获取审批人
        reviewer_id = self.request.POST.get('reviewer')
        approver_id = self.request.POST.get('approver')
        
        # 自动创建审批步骤
        steps_config = [
            (1, 'SUBMIT', '提交', None),  # 提交不需要审批人
            (2, 'REVIEW', '审核', reviewer_id),
            (3, 'APPROVE', '批准', approver_id),
        ]
        
        for step_number, step_name, step_display, approver_id in steps_config:
            step = ApprovalStep.objects.create(
                workflow=self.object,
                step_number=step_number,
                step_name=step_name,
                status='PENDING'
            )
            if approver_id:
                from django.contrib.auth.models import User
                try:
                    step.approver = User.objects.get(pk=approver_id)
                    step.save()
                except User.DoesNotExist:
                    pass
        
        # 第一步自动设为已提交
        first_step = self.object.steps.filter(step_number=1).first()
        if first_step:
            first_step.status = 'APPROVED'
            first_step.approved_at = timezone.now()
            first_step.comments = '已提交'
            first_step.save()
            
            # 设置当前步骤为第2步
            self.object.current_step = 2
            self.object.status = 'IN_PROGRESS'
            self.object.save()
        
        messages.success(self.request, '审批工作流创建成功')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from inspections.models import InspectionPlan
        from reports.models import InspectionReport
        from django.contrib.auth.models import User
        from accounts.models import Role, UserProfile
        
        # 获取待审核的检验计划和报告
        context['plans'] = InspectionPlan.objects.filter(status='PENDING_REVIEW')
        context['reports'] = InspectionReport.objects.filter(status='COMPLETED')
        
        # 获取审核人和批准人角色 - 通过UserProfile的roles字段查询
        try:
            reviewer_role = Role.objects.get(code='REVIEWER')
            # 获取拥有审核员角色的用户
            reviewer_profiles = UserProfile.objects.filter(roles=reviewer_role, is_active=True)
            context['reviewers'] = [p.user for p in reviewer_profiles if p.user.is_active]
        except Role.DoesNotExist:
            # 如果没有审核员角色，使用普通员工
            context['reviewers'] = User.objects.filter(is_active=True, is_superuser=False)
        
        try:
            approver_role = Role.objects.get(code='APPROVER')
            # 获取拥有批准人角色的用户
            approver_profiles = UserProfile.objects.filter(roles=approver_role, is_active=True)
            context['approvers'] = [p.user for p in approver_profiles if p.user.is_active]
        except Role.DoesNotExist:
            # 如果没有批准人角色，使用超级用户
            context['approvers'] = User.objects.filter(is_active=True, is_superuser=True)
        
        return context


class WorkflowUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑审批工作流"""
    model = ApprovalWorkflow
    template_name = 'workflows/workflow_form.html'
    fields = ['notes', 'status']
    permission_module = 'workflows'
    
    def get_success_url(self):
        return reverse_lazy('workflow_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '审批工作流更新成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


class WorkflowDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除审批工作流"""
    model = ApprovalWorkflow
    success_url = reverse_lazy('workflow_list')
    permission_module = 'workflows'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '审批工作流删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# 不合格品处理视图
class NonConformanceListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """不合格品报告列表"""
    model = NonConformanceReport
    template_name = 'workflows/ncr_list.html'
    context_object_name = 'ncrs'
    paginate_by = 20
    permission_module = 'workflows'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'workflows', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'workflows', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'workflows', 'delete')
        return context


class NonConformanceDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """不合格品报告详情"""
    model = NonConformanceReport
    template_name = 'workflows/ncr_detail.html'
    context_object_name = 'ncr'
    permission_module = 'workflows'
    
    def get_context_data(self, **kwargs):
        from django.contrib.auth.models import User
        context = super().get_context_data(**kwargs)
        context['actions'] = self.object.actions.all()
        context['users'] = User.objects.filter(is_active=True).order_by('username')
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'workflows', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'workflows', 'delete')
        return context


class NonConformanceCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建不合格品报告"""
    model = NonConformanceReport
    template_name = 'workflows/ncr_form.html'
    fields = ['part', 'measurement_record', 'product_name', 'specification', 'batch_number', 'department_code',
              'problem_type', 'problem_description', 'defect_phenomenon',
              'supply_method', 'supplier_name', 'delivery_date', 'attachment', 'notes']
    success_url = reverse_lazy('ncr_list')
    permission_module = 'workflows'
    
    def form_valid(self, form):
        form.instance.inspector = self.request.user
        form.instance.inspected_at = timezone.now()
        messages.success(self.request, '不合格品报告创建成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from parts.models import Part
        from measurements.models import MeasurementRecord
        # 获取所有零件（包括非活跃的）
        context['parts'] = Part.objects.all().order_by('part_number')
        context['measurement_records'] = MeasurementRecord.objects.select_related(
            'batch', 'batch__plan', 'batch__plan__part', 'characteristic'
        ).order_by('-measured_at')[:50]
        return context


class NonConformanceUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑不合格品报告"""
    model = NonConformanceReport
    template_name = 'workflows/ncr_form.html'
    fields = ['part', 'measurement_record', 'product_name', 'specification', 'batch_number', 'department_code',
              'problem_type', 'problem_description', 'defect_phenomenon',
              'supply_method', 'supplier_name', 'delivery_date', 'attachment', 
              'notes', 'status']
    permission_module = 'workflows'
    
    def get_success_url(self):
        return reverse_lazy('ncr_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '不合格品报告更新成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from parts.models import Part
        from measurements.models import MeasurementRecord
        # 获取所有零件（包括非活跃的）
        context['parts'] = Part.objects.all().order_by('part_number')
        context['measurement_records'] = MeasurementRecord.objects.select_related(
            'batch', 'batch__plan', 'batch__plan__part', 'characteristic'
        ).order_by('-measured_at')[:50]
        context['is_edit'] = True
        return context


class NonConformanceDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除不合格品报告"""
    model = NonConformanceReport
    success_url = reverse_lazy('ncr_list')
    permission_module = 'workflows'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '不合格品报告删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
