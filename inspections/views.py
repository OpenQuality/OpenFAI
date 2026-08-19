from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from parts.models import CADExtraction, Dimension
from .models import InspectionPlan, CharacteristicCategory, InspectionCharacteristic
from .serializers import (
    InspectionPlanSerializer, InspectionPlanDetailSerializer, 
    InspectionPlanListSerializer, InspectionCharacteristicSerializer,
    CharacteristicCategorySerializer
)
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions


class InspectionPlanViewSet(viewsets.ModelViewSet):
    """检验计划API视图集"""
    queryset = InspectionPlan.objects.all()
    serializer_class = InspectionPlanSerializer
    filterset_fields = ['part', 'standard', 'status']
    search_fields = ['plan_number', 'plan_name', 'part__part_number']
    ordering_fields = ['created_at', 'plan_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InspectionPlanListSerializer
        elif self.action == 'retrieve':
            return InspectionPlanDetailSerializer
        return InspectionPlanSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate_from_cad(self, request, pk=None):
        """从CAD解析结果生成检验特性"""
        plan = self.get_object()
        
        # 获取零件的最新CAD解析结果
        extraction = CADExtraction.objects.filter(
            part=plan.part, status='COMPLETED'
        ).first()
        
        if not extraction:
            return Response(
                {'error': '未找到已完成的CAD解析结果'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not extraction.reviewed:
            return Response(
                {'error': 'AI/OCR识别结果尚未经人工复核确认，请先在图纸识别页面核对每个尺寸的数值、'
                           '公差和气泡位置，确认无误后点击"确认复核"，才能生成正式检验特性。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 从解析结果生成检验特性
        dimensions = extraction.dimensions.all()
        created_count = 0
        
        for idx, dim in enumerate(dimensions, 1):
            char, created = InspectionCharacteristic.objects.get_or_create(
                plan=plan,
                char_number=dim.dim_id,
                defaults={
                    'char_name': dim.name,
                    'char_type': 'DIMENSION' if dim.dim_type in ['LINEAR', 'DIAMETER', 'RADIUS'] else 'GD_T',
                    'nominal_value': dim.nominal_value,
                    'upper_tolerance': dim.upper_tolerance,
                    'lower_tolerance': dim.lower_tolerance,
                    'unit': dim.unit,
                    'is_critical': dim.is_critical,
                    'sequence': idx
                }
            )
            if created:
                created_count += 1
        
        return Response({
            'status': 'success',
            'created_count': created_count,
            'total_count': dimensions.count(),
            'message': f'成功生成{created_count}个检验特性'
        })
    
    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        """提交审核"""
        plan = self.get_object()
        
        if plan.status != 'DRAFT':
            return Response(
                {'error': '只有草稿状态的计划可以提交审核'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan.status = 'PENDING_REVIEW'
        plan.save()
        
        return Response({
            'status': 'success',
            'message': '已提交审核'
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """批准计划"""
        plan = self.get_object()
        
        if plan.status != 'PENDING_REVIEW':
            return Response(
                {'error': '只有待审核状态的计划可以批准'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan.status = 'ACTIVE'
        plan.approved_by = request.user
        plan.approved_at = timezone.now()
        plan.save()
        
        return Response({
            'status': 'success',
            'message': '计划已批准'
        })


class InspectionCharacteristicViewSet(viewsets.ModelViewSet):
    """检验特性API视图集"""
    queryset = InspectionCharacteristic.objects.all()
    serializer_class = InspectionCharacteristicSerializer
    filterset_fields = ['plan', 'char_type', 'is_critical', 'is_key_characteristic']
    ordering_fields = ['sequence', 'char_number']


class CharacteristicCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """特性分类API视图集"""
    queryset = CharacteristicCategory.objects.all()
    serializer_class = CharacteristicCategorySerializer


# 前端视图
class InspectionPlanListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """检验计划列表页面"""
    model = InspectionPlan
    template_name = 'inspections/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 20
    permission_module = 'inspections'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'inspections', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'inspections', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'inspections', 'delete')
        return context


class InspectionPlanDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """检验计划详情页面"""
    model = InspectionPlan
    template_name = 'inspections/plan_detail.html'
    context_object_name = 'plan'
    permission_module = 'inspections'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        characteristics = self.object.characteristics.all()
        context['characteristics'] = characteristics
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'inspections', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'inspections', 'delete')
        # 上下公差均未设置的特性：图纸未识别到公差或人工尚未补充，无法计算Cp/Cpk
        context['no_tolerance_count'] = characteristics.filter(
            upper_tolerance__isnull=True, lower_tolerance__isnull=True
        ).count()
        return context
    
    def post(self, request, *args, **kwargs):
        """处理POST请求，如提交审核"""
        self.object = self.get_object()
        action = request.POST.get('action', '')
        
        if action == 'submit_review' or 'submit_review' in request.POST:
            # 提交审核
            if self.object.status == 'DRAFT':
                self.object.status = 'PENDING_REVIEW'
                self.object.save()
                messages.success(request, '检验计划已提交审核')
            else:
                messages.warning(request, '只有草稿状态的计划可以提交审核')
        
        elif action == 'approve':
            # 批准
            if self.object.status == 'PENDING_REVIEW':
                self.object.status = 'ACTIVE'
                self.object.approved_by = request.user
                self.object.approved_at = timezone.now()
                self.object.save()
                messages.success(request, '检验计划已批准')
            else:
                messages.warning(request, '只有待审核状态的计划可以批准')
        
        elif action == 'reject':
            # 拒绝
            if self.object.status == 'PENDING_REVIEW':
                self.object.status = 'DRAFT'
                self.object.save()
                messages.success(request, '检验计划已拒绝，退回草稿状态')
            else:
                messages.warning(request, '只有待审核状态的计划可以拒绝')
        
        return redirect('plan_detail', pk=self.object.pk)


class InspectionPlanCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建检验计划页面"""
    model = InspectionPlan
    template_name = 'inspections/plan_form.html'
    fields = ['plan_name', 'part', 'standard', 'sample_size', 'description']
    success_url = reverse_lazy('plan_list')
    permission_module = 'inspections'
    
    def get_initial(self):
        initial = super().get_initial()
        # 支持从URL参数预选零件
        part_id = self.request.GET.get('part')
        if part_id:
            try:
                from parts.models import Part
                part = Part.objects.get(pk=part_id)
                initial['part'] = part
                initial['plan_name'] = f'{part.part_number} 检验计划'
            except Part.DoesNotExist:
                pass
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, '检验计划创建成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from parts.models import Part
        # 获取所有零件，不仅仅限制为ACTIVE状态
        context['parts'] = Part.objects.all().order_by('-created_at')
        return context


class InspectionPlanUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑检验计划页面"""
    model = InspectionPlan
    template_name = 'inspections/plan_form.html'
    fields = ['plan_name', 'part', 'standard', 'sample_size', 'description', 'status']
    permission_module = 'inspections'
    
    def get_success_url(self):
        return reverse_lazy('plan_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, '检验计划更新成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from parts.models import Part
        context['parts'] = Part.objects.all().order_by('-created_at')
        context['is_edit'] = True
        return context


class InspectionPlanDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除检验计划"""
    model = InspectionPlan
    success_url = reverse_lazy('plan_list')
    permission_module = 'inspections'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '检验计划删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
