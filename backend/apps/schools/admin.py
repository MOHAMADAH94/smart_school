from django.contrib import admin

from .models import School, SchoolMembership


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'school_code', 'city', 'country', 'is_active', 'created_at')
    search_fields = ('name', 'school_code', 'email', 'phone')
    list_filter = ('is_active', 'country', 'city')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SchoolMembership)
class SchoolMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__username', 'user__email', 'school__name')
