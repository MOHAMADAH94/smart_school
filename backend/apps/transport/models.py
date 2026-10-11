from django.db import models


class VehicleType(models.TextChoices):
    BUS = 'BUS', 'Bus'
    VAN = 'VAN', 'Van'
    MINIBUS = 'MINIBUS', 'Minibus'
    CAR = 'CAR', 'Car'
    OTHER = 'OTHER', 'Other'


class BusDriver(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='bus_drivers',
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True, default='')
    license_number = models.CharField(max_length=64, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Bus(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='buses',
    )
    bus_number = models.CharField(max_length=64)
    vehicle_number = models.CharField(max_length=64, blank=True, default='')
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BUS,
    )
    capacity = models.PositiveIntegerField(default=20)
    driver = models.ForeignKey(
        BusDriver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='buses',
    )
    phone = models.CharField(max_length=32, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['bus_number']
        unique_together = ('school', 'bus_number')

    def __str__(self) -> str:
        return self.bus_number


class BusRoute(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='bus_routes',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    start_location = models.CharField(max_length=255, blank=True, default='')
    end_location = models.CharField(max_length=255, blank=True, default='')
    stops = models.TextField(blank=True, default='', help_text='Comma or newline separated stops')
    bus = models.ForeignKey(
        Bus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routes',
    )
    driver = models.ForeignKey(
        BusDriver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routes',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class TransportStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class StudentTransport(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='student_transports',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='transport_assignments',
    )
    bus = models.ForeignKey(
        Bus,
        on_delete=models.PROTECT,
        related_name='student_assignments',
    )
    route = models.ForeignKey(
        BusRoute,
        on_delete=models.PROTECT,
        related_name='student_assignments',
    )
    pickup_location = models.CharField(max_length=255, blank=True, default='')
    dropoff_location = models.CharField(max_length=255, blank=True, default='')
    transport_start_date = models.DateField(null=True, blank=True)
    transport_end_date = models.DateField(null=True, blank=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=TransportStatus.choices,
        default=TransportStatus.ACTIVE,
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.student} → {self.bus}'
