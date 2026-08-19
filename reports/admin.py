from django.contrib import admin
from .models import ReportTemplate, InspectionReport


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'standard', 'is_active', 'created_at']
    list_filter = ['standard', 'is_active']
    search_fields = ['name']


@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ['report_number', 'title', 'plan', 'status', 'conclusion', 'generated_at']
    list_filter = ['status', 'conclusion', 'generated_at']
    search_fields = ['report_number', 'title', 'plan__plan_number']
    readonly_fields = ['generated_at', 'published_at']
