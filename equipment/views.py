from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import json
from .models import Equipment, EquipmentConnection, MeasurementDataImport
from .serializers import (
    EquipmentSerializer, EquipmentConnectionSerializer,
    MeasurementDataImportSerializer, MeasurementDataUploadSerializer
)
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions


class EquipmentViewSet(viewsets.ModelViewSet):
    """设备API视图集"""
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    filterset_fields = ['equipment_type', 'status']
    search_fields = ['equipment_id', 'equipment_name']
    
    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        """连接设备"""
        equipment = self.get_object()
        
        # 创建连接记录
        connection = EquipmentConnection.objects.create(
            equipment=equipment,
            status='CONNECTED'
        )
        
        # 更新设备状态
        equipment.status = 'ACTIVE'
        equipment.save()
        
        return Response({
            'status': 'success',
            'connection_id': str(connection.id),
            'message': f'设备 {equipment.equipment_name} 已连接'
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """断开设备"""
        equipment = self.get_object()
        
        # 更新最近连接记录
        connection = EquipmentConnection.objects.filter(
            equipment=equipment, status='CONNECTED'
        ).first()
        
        if connection:
            connection.status = 'DISCONNECTED'
            connection.disconnected_at = timezone.now()
            connection.save()
        
        return Response({
            'status': 'success',
            'message': f'设备 {equipment.equipment_name} 已断开'
        })
    
    @action(detail=True, methods=['get'])
    def connection_history(self, request, pk=None):
        """连接历史"""
        equipment = self.get_object()
        connections = equipment.connections.all()[:20]
        serializer = EquipmentConnectionSerializer(connections, many=True)
        return Response(serializer.data)


class EquipmentConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """设备连接API视图集"""
    queryset = EquipmentConnection.objects.all()
    serializer_class = EquipmentConnectionSerializer
    filterset_fields = ['equipment', 'status']


class MeasurementDataImportViewSet(viewsets.ModelViewSet):
    """测量数据导入API视图集"""
    queryset = MeasurementDataImport.objects.all()
    serializer_class = MeasurementDataImportSerializer
    filterset_fields = ['equipment', 'status']
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """上传测量数据"""
        serializer = MeasurementDataUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            equipment = Equipment.objects.get(id=data['equipment_id'])
        except Equipment.DoesNotExist:
            return Response(
                {'error': '设备不存在'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 创建导入记录
        import_record = MeasurementDataImport.objects.create(
            equipment=equipment,
            file_name=data['file_name'],
            status='PROCESSING',
            created_by=request.user
        )
        
        # 模拟数据解析（实际应解析上传的文件）
        # 这里生成示例数据
        sample_data = {
            'measurements': [
                {'char_id': 'DIM001', 'sample': 1, 'value': 50.05},
                {'char_id': 'DIM002', 'sample': 1, 'value': 100.15},
                {'char_id': 'DIM003', 'sample': 1, 'value': 5.02},
            ]
        }
        
        import_record.parsed_data = sample_data
        import_record.total_records = len(sample_data['measurements'])
        import_record.imported_records = len(sample_data['measurements'])
        import_record.status = 'COMPLETED'
        import_record.imported_at = timezone.now()
        import_record.save()
        
        return Response({
            'status': 'success',
            'import_id': str(import_record.id),
            'total_records': import_record.total_records,
            'imported_records': import_record.imported_records
        })
    
    @action(detail=True, methods=['post'])
    def process_import(self, request, pk=None):
        """处理导入数据"""
        import_record = self.get_object()
        
        if import_record.status != 'COMPLETED':
            return Response(
                {'error': '导入记录未完成'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 这里应调用测量模块创建测量记录
        # 简化处理，返回成功
        
        return Response({
            'status': 'success',
            'message': f'成功处理 {import_record.imported_records} 条记录'
        })


# 前端视图
class EquipmentListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """设备列表页面"""
    model = Equipment
    template_name = 'equipment/equipment_list.html'
    context_object_name = 'equipment_list'
    paginate_by = 20
    permission_module = 'equipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'equipment', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'equipment', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'equipment', 'delete')
        return context


class EquipmentDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """设备详情页面"""
    model = Equipment
    template_name = 'equipment/equipment_detail.html'
    context_object_name = 'equipment'
    permission_module = 'equipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'equipment', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'equipment', 'delete')
        context['connections'] = self.object.connections.all()[:10]
        return context
