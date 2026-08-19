from django.contrib import admin
from .models import MeasurementBatch, MeasurementRecord, StatisticalAnalysis


class MeasurementRecordInline(admin.TabularInline):
    """测量记录内联"""
    model = MeasurementRecord
    extra = 0
    readonly_fields = ['deviation', 'status']
    fields = ['characteristic', 'sample_number', 'measured_value', 'deviation', 'status', 'notes']


@admin.register(MeasurementBatch)
class MeasurementBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'plan', 'status', 'measured_by', 'measured_at', 'total_measurements']
    list_filter = ['status', 'equipment_type', 'measured_at']
    search_fields = ['batch_number', 'plan__plan_number']
    readonly_fields = ['created_at']
    inlines = [MeasurementRecordInline]


@admin.register(MeasurementRecord)
class MeasurementRecordAdmin(admin.ModelAdmin):
    list_display = ['characteristic', 'sample_number', 'measured_value', 'deviation', 'status', 'measured_at']
    list_filter = ['status', 'measured_at']
    search_fields = ['characteristic__char_number', 'batch__batch_number']
    readonly_fields = ['deviation', 'status']


@admin.register(StatisticalAnalysis)
class StatisticalAnalysisAdmin(admin.ModelAdmin):
    list_display = ['characteristic', 'batch', 'mean', 'std_dev', 'cp', 'cpk', 'process_capability']
    list_filter = ['characteristic__plan']
    search_fields = ['characteristic__char_number']
