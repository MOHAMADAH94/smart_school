from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'first_name', 'last_name', 'school', 'status')
    list_filter = ('status', 'school')
    search_fields = ('employee_code', 'first_name', 'last_name', 'email')
