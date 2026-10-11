from rest_framework import serializers

from .models import Bus, BusDriver, BusRoute, StudentTransport


class BusDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusDriver
        fields = (
            'id',
            'name',
            'phone',
            'license_number',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class BusSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True, default=None)
    student_count = serializers.IntegerField(source='student_assignments.count', read_only=True)

    class Meta:
        model = Bus
        fields = (
            'id',
            'bus_number',
            'vehicle_number',
            'vehicle_type',
            'capacity',
            'driver',
            'driver_name',
            'phone',
            'notes',
            'is_active',
            'student_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'driver_name', 'student_count')

    def validate_driver(self, driver):
        if driver is None:
            return driver
        if driver.school_id != self.context['request'].school.id:
            raise serializers.ValidationError('السائق لا ينتمي إلى هذه المدرسة.')
        return driver


class BusRouteSerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True, default=None)
    driver_name = serializers.CharField(source='driver.name', read_only=True, default=None)
    driver_phone = serializers.CharField(source='driver.phone', read_only=True, default=None)
    student_count = serializers.IntegerField(source='student_assignments.count', read_only=True)

    class Meta:
        model = BusRoute
        fields = (
            'id',
            'name',
            'description',
            'start_location',
            'end_location',
            'stops',
            'bus',
            'bus_number',
            'driver',
            'driver_name',
            'driver_phone',
            'student_count',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'bus_number',
            'driver_name',
            'driver_phone',
            'student_count',
        )

    def validate(self, attrs):
        school = self.context['request'].school
        for field in ('bus', 'driver'):
            obj = attrs.get(field) or getattr(self.instance, field, None)
            if obj and obj.school_id != school.id:
                raise serializers.ValidationError({field: 'لا ينتمي إلى هذه المدرسة.'})
        return attrs


class StudentTransportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)

    class Meta:
        model = StudentTransport
        fields = (
            'id',
            'student',
            'student_name',
            'bus',
            'bus_number',
            'route',
            'route_name',
            'pickup_location',
            'dropoff_location',
            'transport_start_date',
            'transport_end_date',
            'monthly_fee',
            'status',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'student_name',
            'bus_number',
            'route_name',
        )

    def validate(self, attrs):
        school = self.context['request'].school
        for field in ('student', 'bus', 'route'):
            obj = attrs.get(field) or getattr(self.instance, field, None)
            if obj and obj.school_id != school.id:
                raise serializers.ValidationError({field: 'لا ينتمي إلى هذه المدرسة.'})
        return attrs
