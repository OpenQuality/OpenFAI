from rest_framework import serializers
from .models import ApprovalWorkflow, ApprovalStep, ElectronicSignature, NonConformanceReport, NonConformanceAction


class ElectronicSignatureSerializer(serializers.ModelSerializer):
    """电子签名序列化器"""
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = ElectronicSignature
        fields = '__all__'


class ApprovalStepSerializer(serializers.ModelSerializer):
    """审批步骤序列化器"""
    step_name_display = serializers.ReadOnlyField(source='get_step_name_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    approver_name = serializers.ReadOnlyField(source='approver.username')
    signature = ElectronicSignatureSerializer(read_only=True)
    
    class Meta:
        model = ApprovalStep
        fields = '__all__'


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """审批工作流序列化器"""
    workflow_type_display = serializers.ReadOnlyField(source='get_workflow_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    initiated_by_name = serializers.ReadOnlyField(source='initiated_by.username')
    total_steps = serializers.ReadOnlyField()
    
    class Meta:
        model = ApprovalWorkflow
        fields = '__all__'


class ApprovalWorkflowDetailSerializer(ApprovalWorkflowSerializer):
    """审批工作流详情序列化器"""
    steps = ApprovalStepSerializer(many=True, read_only=True)
    current_step_info = ApprovalStepSerializer(read_only=True)

    class Meta(ApprovalWorkflowSerializer.Meta):
        fields = list(ApprovalWorkflowSerializer.Meta.fields) + ['steps', 'current_step_info']


class NonConformanceActionSerializer(serializers.ModelSerializer):
    """不合格品处理措施序列化器"""
    action_type_display = serializers.ReadOnlyField(source='get_action_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    responsible_person_name = serializers.ReadOnlyField(source='responsible_person.username')

    class Meta:
        model = NonConformanceAction
        fields = '__all__'


class NonConformanceReportSerializer(serializers.ModelSerializer):
    """不合格品报告序列化器"""
    problem_type_display = serializers.ReadOnlyField(source='get_problem_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    actions = NonConformanceActionSerializer(many=True, read_only=True)

    class Meta:
        model = NonConformanceReport
        fields = '__all__'
        read_only_fields = ['ncr_number', 'inspector', 'inspected_at']
