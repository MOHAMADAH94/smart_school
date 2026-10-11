from django.contrib import admin

from .models import AcademicTerm, Assessment, Grade


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'school', 'is_current')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'classroom', 'term', 'max_score', 'school')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'score', 'school')
