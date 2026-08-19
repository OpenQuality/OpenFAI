from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Role, Department


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'full_name', 'department', 'is_active', 'date_joined']
        read_only_fields = ['date_joined']
    
    def get_full_name(self, obj):
        return obj.profile.get_full_name() if hasattr(obj, 'profile') else obj.username
    
    def get_department(self, obj):
        return obj.profile.department if hasattr(obj, 'profile') else ''


class UserProfileSerializer(serializers.ModelSerializer):
    """用户档案序列化器"""
    user = UserSerializer(read_only=True)
    roles_display = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = '__all__'
    
    def get_roles_display(self, obj):
        return [role.name for role in obj.roles.all()]


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    class Meta:
        model = Role
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    """部门序列化器"""
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = '__all__'
    
    def get_user_count(self, obj):
        return UserProfile.objects.filter(department=obj.name).count()
