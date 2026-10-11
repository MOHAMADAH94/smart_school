from rest_framework import serializers

from .models import (
    Feature,
    PlanFeature,
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
)
from .services import get_enabled_features, latest_payment_status


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('id', 'code', 'name', 'description', 'is_active')


class PlanFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = PlanFeature
        fields = ('feature', 'is_enabled', 'limit_value')


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    plan_features = PlanFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = (
            'id',
            'code',
            'name',
            'description',
            'price_annual',
            'currency',
            'is_active',
            'sort_order',
            'plan_features',
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    enabled_features = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id',
            'plan',
            'start_date',
            'end_date',
            'status',
            'display_status',
            'days_remaining',
            'payment_status',
            'enabled_features',
            'created_at',
            'updated_at',
        )

    def get_enabled_features(self, obj):
        return get_enabled_features(obj.school)

    def get_days_remaining(self, obj):
        return obj.days_remaining

    def get_display_status(self, obj):
        return obj.display_status

    def get_payment_status(self, obj):
        return latest_payment_status(obj)


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    school_code = serializers.CharField(source='school.school_code', read_only=True)
    submitted_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPayment
        fields = (
            'id',
            'school',
            'school_name',
            'school_code',
            'subscription',
            'plan',
            'plan_name',
            'plan_code',
            'amount',
            'currency',
            'payment_method',
            'transaction_reference',
            'status',
            'paid_at',
            'period_start',
            'period_end',
            'notes',
            'receipt_file',
            'submitted_by',
            'submitted_by_name',
            'reviewed_by',
            'reviewed_by_name',
            'reviewed_at',
            'review_notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'school',
            'subscription',
            'status',
            'period_start',
            'period_end',
            'submitted_by',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'created_at',
            'updated_at',
            'school_name',
            'school_code',
            'plan_name',
            'plan_code',
            'submitted_by_name',
            'reviewed_by_name',
        )

    def get_submitted_by_name(self, obj):
        if not obj.submitted_by_id:
            return None
        return obj.submitted_by.get_full_name() or obj.submitted_by.username

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by_id:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.username


class SubscriptionPaymentCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_method = serializers.CharField()
    transaction_reference = serializers.CharField(required=False, allow_blank=True, default='')
    paid_at = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate_plan_id(self, value):
        try:
            return SubscriptionPlan.objects.get(id=value, is_active=True)
        except SubscriptionPlan.DoesNotExist as exc:
            raise serializers.ValidationError('الخطة غير موجودة.') from exc

    def validate_payment_method(self, value):
        from .models import PaymentMethod

        valid = {c.value for c in PaymentMethod}
        if value not in valid:
            raise serializers.ValidationError('طريقة دفع غير صالحة.')
        return value


class SubscriptionPaymentReviewSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')
