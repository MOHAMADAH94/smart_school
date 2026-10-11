from django.contrib import admin

from .models import Notification, NotificationPreference, NotificationRead


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'audience', 'school', 'user', 'created_at')
    list_filter = ('type', 'audience', 'is_read')


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'read_at')
    list_filter = ('read_at',)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'category', 'enabled', 'updated_at')
    list_filter = ('category', 'enabled')
