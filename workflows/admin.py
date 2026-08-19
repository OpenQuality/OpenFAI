from django.contrib import admin
from .models import ApprovalWorkflow, ApprovalStep, ElectronicSignature


class ApprovalStepInline(admin.TabularInline):
    """审批步骤内联"""
    model = ApprovalStep
    extra = 0
    readonly_fields = ['approved_at', 'status']


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow_type', 'status', 'current_step', 'initiated_by', 'initiated_at']
    list_filter = ['workflow_type', 'status', 'initiated_at']
    search_fields = ['plan__plan_number', 'report__report_number']
    inlines = [ApprovalStepInline]


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'step_number', 'step_name', 'approver', 'status', 'approved_at']
    list_filter = ['status', 'step_name']
    search_fields = ['workflow__id', 'approver__username']


@admin.register(ElectronicSignature)
class ElectronicSignatureAdmin(admin.ModelAdmin):
    list_display = ['user', 'step', 'signed_at', 'ip_address']
    list_filter = ['signed_at']
    search_fields = ['user__username']
