from django.contrib import admin

from .models import (
    Feature,
    NotificationEventLog,
    PlanFeature,
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
)


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 0


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'price_annual', 'currency', 'is_active', 'sort_order')
    inlines = [PlanFeatureInline]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('school', 'plan', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'plan')


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'school',
        'plan',
        'amount',
        'currency',
        'payment_method',
        'status',
        'paid_at',
        'created_at',
    )
    list_filter = ('status', 'payment_method')
    search_fields = ('transaction_reference', 'school__name', 'school__school_code')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')


@admin.register(NotificationEventLog)
class NotificationEventLogAdmin(admin.ModelAdmin):
    list_display = ('school', 'event_key', 'created_at')
    search_fields = ('event_key', 'school__name')
