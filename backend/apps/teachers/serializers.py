from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.schools.models import SchoolMembership
from apps.schools.roles import Role

from .models import Teacher

User = get_user_model()


class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    username = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password = serializers.CharField(
        required=False, allow_blank=True, write_only=True, min_length=8
    )
    has_login = serializers.SerializerMethodField()
    login_username = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = (
            'id',
            'employee_code',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'email',
            'specialization',
            'hire_date',
            'status',
            'notes',
            'username',
            'password',
            'has_login',
            'login_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'full_name',
            'has_login',
            'login_username',
        )

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
            raise serializers.ValidationError(
                {'password': 'كلمة المرور مطلوبة عند إنشاء حساب الدخول.'}
            )
        if password and not username and not (self.instance and self.instance.user_id):
            raise serializers.ValidationError(
                {'username': 'اسم المستخدم مطلوب مع كلمة المرور.'}
            )
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
        teacher = Teacher.objects.create(school=school, **validated_data)
        if username and password:
            self._attach_login(teacher, school, username, password)
        return teacher

    @transaction.atomic
    def update(self, instance, validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        school = self.context['request'].school
        if username is not None or password is not None:
            uname = (username or '').strip() or (
                instance.user.username if instance.user_id else ''
            )
            if not uname:
                raise serializers.ValidationError(
                    {'username': 'اسم المستخدم مطلوب لإنشاء/تحديث الحساب.'}
                )
            pwd = password or ''
            if not instance.user_id and not pwd:
                raise serializers.ValidationError(
                    {'password': 'كلمة المرور مطلوبة لإنشاء الحساب.'}
                )
            self._attach_login(instance, school, uname, pwd or None)
        return instance

    def _attach_login(self, teacher: Teacher, school, username: str, password: str | None):
        if teacher.user_id:
            user = teacher.user
            if username and username != user.username:
                user.username = username
            if password:
                user.set_password(password)
            if teacher.email:
                user.email = teacher.email
            if teacher.phone and hasattr(user, 'phone'):
                user.phone = teacher.phone
            user.first_name = teacher.first_name
            user.last_name = teacher.last_name
            user.is_active = True
            user.save()
        else:
            if not password:
                raise serializers.ValidationError({'password': 'كلمة المرور مطلوبة.'})
            user = User.objects.create_user(
                username=username,
                email=teacher.email or '',
                password=password,
                first_name=teacher.first_name,
                last_name=teacher.last_name,
            )
            if teacher.phone and hasattr(user, 'phone'):
                user.phone = teacher.phone
                user.save(update_fields=['phone'])
            teacher.user = user
            teacher.save(update_fields=['user', 'updated_at'])

        SchoolMembership.objects.update_or_create(
            user=user,
            school=school,
            defaults={'role': Role.TEACHER, 'is_active': True},
        )
