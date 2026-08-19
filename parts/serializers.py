from rest_framework import serializers
from .models import (
    Part, CADExtraction, Dimension, DimensionTemplate,
    ControlRequirement, RiskPoint, SOPDocument, Model3DAnalysis,
    SurfaceZone, DrawingReview, StandardInterpretation, InspectionSOPItem,
    PartAttachment
)


class PartAttachmentSerializer(serializers.ModelSerializer):
    """零件附件序列化器"""
    file_type_display = serializers.ReadOnlyField(source='get_file_type_display')
    ocr_status_display = serializers.ReadOnlyField(source='get_ocr_status_display')
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.username')
    
    class Meta:
        model = PartAttachment
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'uploaded_at']


class DimensionSerializer(serializers.ModelSerializer):
    """尺寸序列化器"""
    tolerance_range = serializers.ReadOnlyField()
    
    class Meta:
        model = Dimension
        fields = '__all__'


class CADExtractionSerializer(serializers.ModelSerializer):
    """CAD解析序列化器"""
    dimensions = DimensionSerializer(many=True, read_only=True)
    dimensions_count = serializers.SerializerMethodField()
    extraction_dimensions = serializers.SerializerMethodField()
    
    class Meta:
        model = CADExtraction
        fields = ['id', 'part', 'extraction_data', 'status', 'error_message', 
                  'extracted_at', 'created_at', 'dimensions', 'dimensions_count',
                  'extraction_dimensions']
    
    def get_dimensions_count(self, obj):
        # 优先返回Dimension表的记录数，如果没有则返回extraction_data中的数量
        db_count = obj.dimensions.count()
        if db_count > 0:
            return db_count
        # 从extraction_data中获取
        extraction_dims = obj.extraction_data.get('dimensions', [])
        return len(extraction_dims)
    
    def get_extraction_dimensions(self, obj):
        # 返回extraction_data中的dimensions数据
        return obj.extraction_data.get('dimensions', [])


class DimensionTemplateSerializer(serializers.ModelSerializer):
    """尺寸模板序列化器"""
    dimensions_count = serializers.ReadOnlyField()
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    template_type_display = serializers.ReadOnlyField(source='get_template_type_display')
    
    class Meta:
        model = DimensionTemplate
        fields = '__all__'
        read_only_fields = ['created_by']


class ControlRequirementSerializer(serializers.ModelSerializer):
    """控制要求序列化器"""
    control_type_display = serializers.ReadOnlyField(source='get_control_type_display')
    risk_level_display = serializers.ReadOnlyField(source='get_risk_level_display')
    
    class Meta:
        model = ControlRequirement
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class RiskPointSerializer(serializers.ModelSerializer):
    """关键风险点序列化器"""
    severity_display = serializers.ReadOnlyField(source='get_severity_display')
    related_requirements_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RiskPoint
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_related_requirements_count(self, obj):
        return obj.related_requirements.count()


class SOPDocumentSerializer(serializers.ModelSerializer):
    """SOP文档序列化器"""
    document_type_display = serializers.ReadOnlyField(source='get_document_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.username')
    control_requirements_count = serializers.SerializerMethodField()
    risk_points_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SOPDocument
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'document_number']
    
    def get_control_requirements_count(self, obj):
        return obj.control_requirements.count()
    
    def get_risk_points_count(self, obj):
        return obj.risk_points.count()


class Model3DAnalysisSerializer(serializers.ModelSerializer):
    """3D模型解析序列化器"""
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = Model3DAnalysis
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PartSerializer(serializers.ModelSerializer):
    """零件序列化器"""
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    cad_filename = serializers.ReadOnlyField()
    extractions_count = serializers.SerializerMethodField()
    dimensions_count = serializers.SerializerMethodField()
    control_requirements_count = serializers.SerializerMethodField()
    risk_points_count = serializers.SerializerMethodField()
    sop_documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Part
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by']
    
    def get_extractions_count(self, obj):
        return obj.extractions.count()
    
    def get_dimensions_count(self, obj):
        return obj.dimensions.count()
    
    def get_control_requirements_count(self, obj):
        return obj.control_requirements.count()
    
    def get_risk_points_count(self, obj):
        return obj.risk_points.count()
    
    def get_sop_documents_count(self, obj):
        return obj.sop_documents.count()


class PartListSerializer(serializers.ModelSerializer):
    """零件列表序列化器（简化版）"""
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = Part
        fields = ['id', 'part_number', 'part_name', 'revision', 'customer', 
                  'status', 'status_display', 'created_by_name', 'created_at']


class SurfaceZoneSerializer(serializers.ModelSerializer):
    """外观面区域序列化器"""
    zone_type_display = serializers.ReadOnlyField(source='get_zone_type_display')
    
    class Meta:
        model = SurfaceZone
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class DrawingReviewSerializer(serializers.ModelSerializer):
    """图纸评审序列化器"""
    translation_status_display = serializers.ReadOnlyField(source='get_translation_status_display')
    internal_control_status_display = serializers.ReadOnlyField(source='get_internal_control_status_display')
    completeness_status_display = serializers.ReadOnlyField(source='get_completeness_status_display')
    overall_status_display = serializers.ReadOnlyField(source='get_overall_status_display')
    reviewed_by_name = serializers.ReadOnlyField(source='reviewed_by.username')
    
    class Meta:
        model = DrawingReview
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'reviewed_by', 'reviewed_at']


class StandardInterpretationSerializer(serializers.ModelSerializer):
    """技术标准解读序列化器"""
    
    class Meta:
        model = StandardInterpretation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class InspectionSOPItemSerializer(serializers.ModelSerializer):
    """检验SOP项目序列化器"""
    category_display = serializers.ReadOnlyField(source='get_category_display')
    surface_zone_info = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionSOPItem
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_surface_zone_info(self, obj):
        if obj.surface_zone:
            return {
                'zone_id': obj.surface_zone.zone_id,
                'zone_type': obj.surface_zone.zone_type
            }
        return None
