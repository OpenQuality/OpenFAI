from django.contrib import admin
from .models import InspectionPlan, CharacteristicCategory, InspectionCharacteristic


class InspectionCharacteristicInline(admin.TabularInline):
    """检验特性内联"""
    model = InspectionCharacteristic
    extra = 0
    fields = ['char_number', 'char_name', 'char_type', 'nominal_value', 
              'upper_tolerance', 'lower_tolerance', 'is_critical']
    readonly_fields = []


@admin.register(InspectionPlan)
class InspectionPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_number', 'plan_name', 'part', 'standard', 'status', 'created_at']
    list_filter = ['standard', 'status', 'created_at']
    search_fields = ['plan_number', 'plan_name', 'part__part_number']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    inlines = [InspectionCharacteristicInline]


@admin.register(CharacteristicCategory)
class CharacteristicCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'description']
    search_fields = ['name', 'code']


@admin.register(InspectionCharacteristic)
class InspectionCharacteristicAdmin(admin.ModelAdmin):
    list_display = ['char_number', 'char_name', 'plan', 'char_type', 
                    'nominal_value', 'is_critical', 'sequence']
    list_filter = ['char_type', 'is_critical', 'measurement_method']
    search_fields = ['char_number', 'char_name', 'plan__plan_number']
