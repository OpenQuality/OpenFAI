from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Avg, StdDev, Min, Max, Count
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from decimal import Decimal
import math
from inspections.models import InspectionPlan, InspectionCharacteristic
from .models import MeasurementBatch, MeasurementRecord, StatisticalAnalysis
from .serializers import (
    MeasurementBatchSerializer, MeasurementBatchDetailSerializer,
    MeasurementRecordSerializer, StatisticalAnalysisSerializer,
    MeasurementInputSerializer
)
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions


class MeasurementBatchViewSet(viewsets.ModelViewSet):
    """测量批次API视图集"""
    queryset = MeasurementBatch.objects.all()
    serializer_class = MeasurementBatchSerializer
    filterset_fields = ['plan', 'status', 'equipment_type']
    search_fields = ['batch_number', 'plan__plan_number']
    ordering_fields = ['measured_at', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MeasurementBatchDetailSerializer
        return MeasurementBatchSerializer
    
    def _calculate_all_statistics(self, batch):
        """计算批次所有特性的统计数据（代理到模型方法）"""
        return batch.calculate_all_statistics()

    @action(detail=True, methods=['post'])
    def add_measurement(self, request, pk=None):
        """添加测量数据"""
        batch = self.get_object()
        serializer = MeasurementInputSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # 获取检验特性
        try:
            characteristic = InspectionCharacteristic.objects.get(id=data['characteristic_id'])
        except InspectionCharacteristic.DoesNotExist:
            return Response(
                {'error': '检验特性不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 创建测量记录（捕获唯一约束冲突等数据库错误，避免未处理异常导致返回HTML错误页
        # 而非JSON，使前端fetch().json()解析失败报"Unexpected token '<'"）
        try:
            record = MeasurementRecord.objects.create(
                batch=batch,
                characteristic=characteristic,
                sample_number=data['sample_number'],
                measured_value=data['measured_value'],
                notes=data.get('notes', '')
            )
        except IntegrityError:
            return Response(
                {'error': f"该特性的样本号 {data['sample_number']} 已存在测量记录，请使用其他样本号"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 自动计算该特性的统计数据
        calculated_count = self._calculate_all_statistics(batch)
        
        return Response({
            'status': 'success',
            'record_id': str(record.id),
            'status_result': record.status,
            'deviation': record.deviation,
            'calculated_count': calculated_count,
            'message': f'录入成功，已更新{calculated_count}个特性的统计'
        })
    
    @action(detail=True, methods=['post'])
    def batch_upload(self, request, pk=None):
        """批量上传测量数据"""
        batch = self.get_object()
        measurements = request.data.get('measurements', [])
        
        if not measurements:
            return Response(
                {'error': '请提供测量数据'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_count = 0
        errors = []

        for index, item in enumerate(measurements, 1):
            # 复用与add_measurement相同的序列化器进行校验和类型转换：
            # measured_value必须经DecimalField转换为Decimal后再保存，否则与
            # nominal_value(Decimal)相减时会抛TypeError，导致整条记录创建失败
            item_serializer = MeasurementInputSerializer(data=item)
            if not item_serializer.is_valid():
                errors.append(f'第{index}行：{item_serializer.errors}')
                continue

            data = item_serializer.validated_data
            try:
                characteristic = InspectionCharacteristic.objects.get(
                    id=data['characteristic_id']
                )
                MeasurementRecord.objects.create(
                    batch=batch,
                    characteristic=characteristic,
                    sample_number=data['sample_number'],
                    measured_value=data['measured_value'],
                    notes=data.get('notes', '')
                )
                created_count += 1
            except InspectionCharacteristic.DoesNotExist:
                errors.append(f'第{index}行：检验特性不存在')
            except Exception as e:
                if 'UNIQUE' in str(e).upper() or 'unique' in str(e):
                    errors.append(f'第{index}行：该特性的样本号{data.get("sample_number")}已存在测量记录')
                else:
                    errors.append(f'第{index}行：{e}')

        # 自动计算统计数据
        calculated_count = self._calculate_all_statistics(batch)

        return Response({
            'status': 'success' if created_count > 0 else 'error',
            'created_count': created_count,
            'error_count': len(errors),
            'errors': errors,
            'calculated_count': calculated_count,
            'message': f'录入{created_count}条，失败{len(errors)}条，已更新{calculated_count}个特性的统计'
                       if created_count > 0 else f'全部{len(errors)}条记录录入失败，请检查后重试'
        }, status=status.HTTP_200_OK if created_count > 0 else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def calculate_statistics(self, request, pk=None):
        """计算统计数据"""
        batch = self.get_object()
        calculated_count = self._calculate_all_statistics(batch)
        
        return Response({
            'status': 'success',
            'calculated_count': calculated_count,
            'message': f'成功计算{calculated_count}个特性的统计数据'
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """完成测量"""
        batch = self.get_object()
        batch.status = 'COMPLETED'
        batch.save()
        
        # 自动计算统计
        calculated_count = self._calculate_all_statistics(batch)
        
        return Response({
            'status': 'success',
            'message': f'测量已完成，已计算{calculated_count}个特性的统计'
        })


class MeasurementRecordViewSet(viewsets.ModelViewSet):
    """测量记录API视图集"""
    queryset = MeasurementRecord.objects.all()
    serializer_class = MeasurementRecordSerializer
    filterset_fields = ['batch', 'characteristic', 'status']


class StatisticalAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """统计分析API视图集"""
    queryset = StatisticalAnalysis.objects.all()
    serializer_class = StatisticalAnalysisSerializer
    filterset_fields = ['characteristic', 'batch']


# 前端视图
class MeasurementBatchListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """测量批次列表页面"""
    model = MeasurementBatch
    template_name = 'measurements/batch_list.html'
    context_object_name = 'batches'
    paginate_by = 20
    permission_module = 'measurements'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'measurements', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'measurements', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'measurements', 'delete')
        return context


class MeasurementBatchDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """测量批次详情页面"""
    model = MeasurementBatch
    template_name = 'measurements/batch_detail.html'
    context_object_name = 'batch'
    permission_module = 'measurements'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['records'] = self.object.records.select_related('characteristic').all()
        context['statistics'] = self.object.statistics.all()
        context['characteristics'] = self.object.plan.characteristics.all()
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'measurements', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'measurements', 'delete')
        return context


class MeasurementBatchCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建测量批次"""
    model = MeasurementBatch
    template_name = 'measurements/batch_form.html'
    fields = ['plan', 'equipment_type', 'equipment_id', 'environment_temp', 'environment_humidity', 'notes']
    success_url = reverse_lazy('batch_list')
    permission_module = 'measurements'
    
    def get_initial(self):
        initial = super().get_initial()
        # 支持从URL参数预选检验计划
        plan_id = self.request.GET.get('plan')
        if plan_id:
            try:
                plan = InspectionPlan.objects.get(pk=plan_id)
                initial['plan'] = plan
            except InspectionPlan.DoesNotExist:
                pass
        return initial
    
    def form_valid(self, form):
        form.instance.measured_by = self.request.user
        messages.success(self.request, '测量批次创建成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = InspectionPlan.objects.filter(status='ACTIVE')
        return context


class MeasurementBatchUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑测量批次"""
    model = MeasurementBatch
    template_name = 'measurements/batch_form.html'
    fields = ['equipment_type', 'equipment_id', 'environment_temp', 'environment_humidity', 'notes', 'status']
    permission_module = 'measurements'
    
    def get_success_url(self):
        return reverse_lazy('batch_list')
    
    def form_valid(self, form):
        messages.success(self.request, '测量批次更新成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


class MeasurementBatchDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除测量批次"""
    model = MeasurementBatch
    success_url = reverse_lazy('batch_list')
    permission_module = 'measurements'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '测量批次删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# ==================== Cp/Cpk 分析页面视图 ====================

class CpkAnalysisView(AutoPermissionMixin, LoginRequiredMixin, TemplateView):
    """Cp/Cpk过程能力分析页面"""
    template_name = 'measurements/cpk_analysis.html'
    permission_module = 'measurements'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有统计分析记录（使用 calculated_at 排序）
        all_statistics = StatisticalAnalysis.objects.select_related(
            'characteristic', 'batch'
        ).order_by('-calculated_at')
        
        # 按Cpk分组统计（需要在切片前过滤）
        cpk_excellent = all_statistics.filter(cpk__gte=1.67).count()
        cpk_good = all_statistics.filter(cpk__gte=1.33, cpk__lt=1.67).count()
        cpk_acceptable = all_statistics.filter(cpk__gte=1.0, cpk__lt=1.33).count()
        cpk_poor = all_statistics.filter(cpk__gte=0, cpk__lt=1.0).count()
        
        # 获取前100条记录用于展示
        statistics = all_statistics[:100]
        
        context['statistics'] = statistics
        context['cpk_stats'] = {
            'excellent': cpk_excellent,
            'good': cpk_good,
            'acceptable': cpk_acceptable,
            'poor': cpk_poor,
            'total': all_statistics.count(),
        }
        
        # 获取最近的分析记录（用于图表）
        recent_stats = all_statistics[:50]
        
        # 构建图表数据
        chart_labels = []
        chart_cpk = []
        chart_cp = []
        for stat in reversed(recent_stats):
            chart_labels.append(stat.characteristic.char_number[:20])
            chart_cpk.append(float(stat.cpk) if stat.cpk else 0)
            chart_cp.append(float(stat.cp) if stat.cp else 0)
        
        context['chart_data'] = {
            'labels': chart_labels,
            'cpk': chart_cpk,
            'cp': chart_cp,
        }
        
        return context
