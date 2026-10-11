from django.contrib import admin

from .models import Parent, StudentParent


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'relationship', 'school')
    search_fields = ('name', 'phone', 'email')


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent', 'relationship', 'is_primary', 'school')
