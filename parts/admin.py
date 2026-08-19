from django.contrib import admin
from .models import Part, CADExtraction, Dimension, PartAttachment


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'part_name', 'revision', 'customer', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['part_number', 'part_name', 'customer']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PartAttachment)
class PartAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'file_type', 'part', 'ocr_status', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'ocr_status', 'uploaded_at']
    search_fields = ['file_name', 'part__part_number']
    readonly_fields = ['uploaded_at']


@admin.register(CADExtraction)
class CADExtractionAdmin(admin.ModelAdmin):
    list_display = ['part', 'status', 'extracted_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['part__part_number']


@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):
    list_display = ['dim_id', 'name', 'dim_type', 'nominal_value', 'upper_tolerance', 'lower_tolerance', 'is_critical']
    list_filter = ['dim_type', 'is_critical', 'extraction__part']
    search_fields = ['dim_id', 'name']
