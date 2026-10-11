from rest_framework import serializers

from apps.schools.roles import Role
from apps.schools.services import membership_permissions

from .models import School, SchoolMembership
from .services import create_school_with_owner


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = (
            'id',
            'name',
            'logo',
            'phone',
            'email',
            'address',
            'city',
            'country',
            'academic_year',
            'school_code',
            'slug',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'school_code',
            'slug',
            'is_active',
            'created_at',
            'updated_at',
        )


class CreateSchoolSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(max_length=512, required=False, allow_blank=True)
    city = serializers.CharField(max_length=128, required=False, allow_blank=True)
    country = serializers.CharField(max_length=128, required=False, allow_blank=True)
    academic_year = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def create(self, validated_data):
        user = self.context['request'].user
        school, membership = create_school_with_owner(user=user, school_data=validated_data)
        self.context['membership'] = membership
        return school


class SchoolMembershipSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = SchoolMembership
        fields = (
            'id',
            'school',
            'role',
            'role_display',
            'is_active',
            'permissions',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_permissions(self, obj):
        return membership_permissions(obj)


class MembershipInviteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=Role.CHOICES)

    def validate_role(self, value):
        if value == Role.SUPER_ADMIN:
            raise serializers.ValidationError('لا يمكن تعيين دور المشرف العام من هنا.')
        return value
