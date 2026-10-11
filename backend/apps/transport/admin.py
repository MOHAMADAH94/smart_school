from django.contrib import admin

from .models import Bus, BusDriver, BusRoute, StudentTransport


@admin.register(BusDriver)
class BusDriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'school', 'is_active')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_number', 'vehicle_type', 'capacity', 'driver', 'school', 'is_active')


@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'bus', 'driver', 'school', 'is_active')


@admin.register(StudentTransport)
class StudentTransportAdmin(admin.ModelAdmin):
    list_display = ('student', 'bus', 'route', 'status', 'monthly_fee', 'school')
