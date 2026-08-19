from django.contrib import admin
from .models import Equipment, EquipmentConnection, MeasurementDataImport


class EquipmentConnectionInline(admin.TabularInline):
    """设备连接内联"""
    model = EquipmentConnection
    extra = 0
    readonly_fields = ['connected_at', 'disconnected_at']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment_id', 'equipment_name', 'equipment_type', 'status', 'last_calibration_date']
    list_filter = ['equipment_type', 'status']
    search_fields = ['equipment_id', 'equipment_name']
    inlines = [EquipmentConnectionInline]


@admin.register(EquipmentConnection)
class EquipmentConnectionAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'status', 'connected_at', 'disconnected_at']
    list_filter = ['status', 'connected_at']
    search_fields = ['equipment__equipment_id']


@admin.register(MeasurementDataImport)
class MeasurementDataImportAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'file_name', 'status', 'total_records', 'imported_records', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['equipment__equipment_id', 'file_name']
