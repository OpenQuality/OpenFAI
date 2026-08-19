from rest_framework import serializers
from .models import MeasurementBatch, MeasurementRecord, StatisticalAnalysis


class MeasurementRecordSerializer(serializers.ModelSerializer):
    """测量记录序列化器"""
    char_number = serializers.ReadOnlyField(source='characteristic.char_number')
    char_name = serializers.ReadOnlyField(source='characteristic.char_name')
    nominal_value = serializers.ReadOnlyField(source='characteristic.nominal_value')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = MeasurementRecord
        fields = '__all__'


class StatisticalAnalysisSerializer(serializers.ModelSerializer):
    """统计分析序列化器"""
    char_number = serializers.ReadOnlyField(source='characteristic.char_number')
    process_capability = serializers.ReadOnlyField()
    
    class Meta:
        model = StatisticalAnalysis
        fields = '__all__'


class MeasurementBatchSerializer(serializers.ModelSerializer):
    """测量批次序列化器"""
    plan_number = serializers.ReadOnlyField(source='plan.plan_number')
    plan_name = serializers.ReadOnlyField(source='plan.plan_name')
    measured_by_name = serializers.ReadOnlyField(source='measured_by.username')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    total_measurements = serializers.ReadOnlyField()
    pass_count = serializers.ReadOnlyField()
    fail_count = serializers.ReadOnlyField()
    
    class Meta:
        model = MeasurementBatch
        fields = '__all__'
        read_only_fields = ['reviewed_by', 'reviewed_at']


class MeasurementBatchDetailSerializer(MeasurementBatchSerializer):
    """测量批次详情序列化器"""
    records = MeasurementRecordSerializer(many=True, read_only=True)
    statistics = StatisticalAnalysisSerializer(many=True, read_only=True)
    
    class Meta(MeasurementBatchSerializer.Meta):
        fields = list(MeasurementBatchSerializer.Meta.fields) + ['records', 'statistics']


class MeasurementInputSerializer(serializers.Serializer):
    """测量数据输入序列化器"""
    characteristic_id = serializers.UUIDField()
    sample_number = serializers.IntegerField(min_value=1)
    measured_value = serializers.DecimalField(max_digits=15, decimal_places=6)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
