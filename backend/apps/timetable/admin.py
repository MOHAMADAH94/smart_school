from django.contrib import admin

from .models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    WeeklySubjectRequirement,
)


class TimetablePeriodInline(admin.TabularInline):
    model = TimetablePeriod
    extra = 0


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'academic_year', 'status', 'published_at')
    list_filter = ('status', 'academic_year')
    inlines = [TimetablePeriodInline]


@admin.register(WeeklySubjectRequirement)
class WeeklySubjectRequirementAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'classroom', 'subject', 'lessons_per_week')
    list_filter = ('timetable',)


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'day', 'period', 'classroom', 'subject')
    list_filter = ('timetable', 'day')


@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'day', 'period_number', 'is_available')
    list_filter = ('day', 'is_available')
