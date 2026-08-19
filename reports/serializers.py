from rest_framework import serializers
from .models import (
    ReportTemplate, InspectionReport,
    MaterialCertification, SpecialProcessRecord, FunctionalTestRecord,
)


class MaterialCertificationSerializer(serializers.ModelSerializer):
    """Form2-原材料证书序列化器"""
    class Meta:
        model = MaterialCertification
        fields = '__all__'


class SpecialProcessRecordSerializer(serializers.ModelSerializer):
    """Form2-特殊工艺记录序列化器"""
    process_type_display = serializers.ReadOnlyField(source='get_process_type_display')

    class Meta:
        model = SpecialProcessRecord
        fields = '__all__'


class FunctionalTestRecordSerializer(serializers.ModelSerializer):
    """Form2-功能测试记录序列化器"""
    class Meta:
        model = FunctionalTestRecord
        fields = '__all__'


class ReportTemplateSerializer(serializers.ModelSerializer):
    """报告模板序列化器"""
    standard_display = serializers.ReadOnlyField(source='get_standard_display')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = ReportTemplate
        fields = '__all__'


class InspectionReportSerializer(serializers.ModelSerializer):
    """检验报告序列化器"""
    plan_number = serializers.ReadOnlyField(source='plan.plan_number')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    generated_by_name = serializers.ReadOnlyField(source='generated_by.username')
    template_name = serializers.ReadOnlyField(source='template.name')
    
    class Meta:
        model = InspectionReport
        fields = '__all__'
        read_only_fields = ['generated_at', 'published_at', 'generated_by', 'published_by']


class InspectionReportDetailSerializer(InspectionReportSerializer):
    """检验报告详情序列化器"""
    batch_data = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    
    class Meta(InspectionReportSerializer.Meta):
        fields = list(InspectionReportSerializer.Meta.fields) + ['batch_data', 'statistics']
    
    def get_batch_data(self, obj):
        return {
            'batch_number': obj.batch.batch_number,
            'plan_name': obj.plan.plan_name,
            'part_number': obj.plan.part.part_number,
            'part_name': obj.plan.part.part_name,
            'measured_at': obj.batch.measured_at,
            'measured_by': obj.batch.measured_by.username if obj.batch.measured_by else None,
            'total_measurements': obj.batch.total_measurements,
            'pass_count': obj.batch.pass_count,
            'fail_count': obj.batch.fail_count,
        }
    
    def get_statistics(self, obj):
        from measurements.models import StatisticalAnalysis
        stats = StatisticalAnalysis.objects.filter(batch=obj.batch)
        return [{
            'char_number': s.characteristic.char_number,
            'char_name': s.characteristic.char_name,
            'mean': s.mean,
            'std_dev': s.std_dev,
            'cpk': s.cpk,
            'process_capability': s.process_capability,
        } for s in stats]
