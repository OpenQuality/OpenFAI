from rest_framework import serializers
from .models import Equipment, EquipmentConnection, MeasurementDataImport


class EquipmentSerializer(serializers.ModelSerializer):
    """设备序列化器"""
    equipment_type_display = serializers.ReadOnlyField(source='get_equipment_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    responsible_person_name = serializers.ReadOnlyField(source='responsible_person.username')
    
    class Meta:
        model = Equipment
        fields = '__all__'


class EquipmentConnectionSerializer(serializers.ModelSerializer):
    """设备连接序列化器"""
    equipment_name = serializers.ReadOnlyField(source='equipment.equipment_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = EquipmentConnection
        fields = '__all__'


class MeasurementDataImportSerializer(serializers.ModelSerializer):
    """测量数据导入序列化器"""
    equipment_name = serializers.ReadOnlyField(source='equipment.equipment_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = MeasurementDataImport
        fields = '__all__'


class MeasurementDataUploadSerializer(serializers.Serializer):
    """测量数据上传序列化器"""
    equipment_id = serializers.UUIDField()
    file_name = serializers.CharField(max_length=255)
    file_data = serializers.FileField()
