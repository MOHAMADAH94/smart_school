from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.schools.models import SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student

from .models import Parent, StudentParent

User = get_user_model()


class ParentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, min_length=8)
    has_login = serializers.SerializerMethodField()
    login_username = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = (
            'id',
            'name',
            'phone',
            'email',
            'address',
            'relationship',
            'username',
            'password',
            'has_login',
            'login_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'has_login', 'login_username')

    def get_has_login(self, obj):
        return bool(obj.user_id)

    def get_login_username(self, obj):
        if not obj.user_id:
            return None
        return obj.user.username

    def validate(self, attrs):
        username = (attrs.get('username') or '').strip()
        password = attrs.get('password') or ''
        if username and not password and not self.instance:
            raise serializers.ValidationError({'password': 'كلمة المرور مطلوبة عند إنشاء حساب الدخول.'})
        if password and not username and not (self.instance and self.instance.user_id):
            raise serializers.ValidationError({'username': 'اسم المستخدم مطلوب مع كلمة المرور.'})
        if username:
            qs = User.objects.filter(username__iexact=username)
            if self.instance and self.instance.user_id:
                qs = qs.exclude(pk=self.instance.user_id)
            if qs.exists():
                raise serializers.ValidationError({'username': 'اسم المستخدم مستخدم مسبقاً.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        username = (validated_data.pop('username', '') or '').strip()
        password = validated_data.pop('password', '') or ''
        school = validated_data.pop('school', None) or self.context['request'].school
        parent = Parent.objects.create(school=school, **validated_data)
        if username and password:
            self._attach_login(parent, school, username, password)
        return parent

    @transaction.atomic
    def update(self, instance, validated_data):
        username = (validated_data.pop('username', None))
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        school = self.context['request'].school
        if username is not None or password is not None:
            uname = (username or '').strip() or (instance.user.username if instance.user_id else '')
            if not uname:
                raise serializers.ValidationError({'username': 'اسم المستخدم مطلوب لإنشاء/تحديث الحساب.'})
            pwd = password or ''
            if not instance.user_id and not pwd:
                raise serializers.ValidationError({'password': 'كلمة المرور مطلوبة لإنشاء الحساب.'})
            self._attach_login(instance, school, uname, pwd or None)
        return instance

    def _attach_login(self, parent: Parent, school, username: str, password: str | None):
        if parent.user_id:
            user = parent.user
            if username and username != user.username:
                user.username = username
            if password:
                user.set_password(password)
            if parent.email:
                user.email = parent.email
            if parent.phone and hasattr(user, 'phone'):
                user.phone = parent.phone
            user.is_active = True
            user.save()
        else:
            if not password:
                raise serializers.ValidationError({'password': 'كلمة المرور مطلوبة.'})
            user = User.objects.create_user(
                username=username,
                email=parent.email or '',
                password=password,
            )
            if parent.phone and hasattr(user, 'phone'):
                user.phone = parent.phone
                user.save(update_fields=['phone'])
            parent.user = user
            parent.save(update_fields=['user', 'updated_at'])

        SchoolMembership.objects.update_or_create(
            user=user,
            school=school,
            defaults={'role': Role.PARENT, 'is_active': True},
        )


class StudentParentSerializer(serializers.ModelSerializer):
    parent_detail = ParentSerializer(source='parent', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = StudentParent
        fields = (
            'id',
            'student',
            'student_name',
            'parent',
            'parent_detail',
            'relationship',
            'is_primary',
            'created_at',
        )
        read_only_fields = ('id', 'created_at', 'student_name', 'parent_detail')

    def validate(self, attrs):
        request = self.context['request']
        school = request.school
        student = attrs.get('student') or getattr(self.instance, 'student', None)
        parent = attrs.get('parent') or getattr(self.instance, 'parent', None)
        if student and student.school_id != school.id:
            raise serializers.ValidationError({'student': 'الطالب لا ينتمي إلى هذه المدرسة.'})
        if parent and parent.school_id != school.id:
            raise serializers.ValidationError({'parent': 'ولي الأمر لا ينتمي إلى هذه المدرسة.'})
        return attrs
