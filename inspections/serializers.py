from rest_framework import serializers
from .models import InspectionPlan, CharacteristicCategory, InspectionCharacteristic


class CharacteristicCategorySerializer(serializers.ModelSerializer):
    """特性分类序列化器"""
    class Meta:
        model = CharacteristicCategory
        fields = '__all__'


class InspectionCharacteristicSerializer(serializers.ModelSerializer):
    """检验特性序列化器"""
    char_type_display = serializers.ReadOnlyField(source='get_char_type_display')
    measurement_method_display = serializers.ReadOnlyField(source='get_measurement_method_display')
    upper_limit = serializers.ReadOnlyField()
    lower_limit = serializers.ReadOnlyField()
    tolerance_band = serializers.ReadOnlyField()
    
    class Meta:
        model = InspectionCharacteristic
        fields = '__all__'


class InspectionPlanSerializer(serializers.ModelSerializer):
    """检验计划序列化器"""
    part_number = serializers.ReadOnlyField(source='part.part_number')
    part_name = serializers.ReadOnlyField(source='part.part_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    standard_display = serializers.ReadOnlyField(source='get_standard_display')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    characteristics_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionPlan
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'approved_by', 'approved_at']
    
    def get_characteristics_count(self, obj):
        return obj.characteristics.count()


class InspectionPlanDetailSerializer(InspectionPlanSerializer):
    """检验计划详情序列化器"""
    characteristics = InspectionCharacteristicSerializer(many=True, read_only=True)
    
    class Meta(InspectionPlanSerializer.Meta):
        fields = list(InspectionPlanSerializer.Meta.fields) + ['characteristics']


class InspectionPlanListSerializer(serializers.ModelSerializer):
    """检验计划列表序列化器（简化版）"""
    part_number = serializers.ReadOnlyField(source='part.part_number')
    part_name = serializers.ReadOnlyField(source='part.part_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    characteristics_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionPlan
        fields = ['id', 'plan_number', 'plan_name', 'part_number', 'part_name',
                  'standard', 'status', 'status_display', 'characteristics_count',
                  'created_by_name', 'created_at']
    
    def get_characteristics_count(self, obj):
        return obj.characteristics.count()
