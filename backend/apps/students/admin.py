from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_code', 'first_name', 'last_name', 'school', 'classroom', 'status')
    list_filter = ('status', 'gender', 'school')
    search_fields = ('student_code', 'first_name', 'last_name', 'father_name')
