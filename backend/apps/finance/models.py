from django.db import models


class Fee(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='fees')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='fees')
    title = models.CharField(max_length=255, default='Annual Student Fee')
    academic_year = models.CharField(max_length=32, blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.title} — {self.student}'

    @property
    def paid_amount(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount


class Payment(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='payments')
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name='payments')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    method = models.CharField(max_length=64, blank=True, default='cash')
    reference = models.CharField(max_length=128, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']


class Expense(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=128, blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date']


class Invoice(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='invoices')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='invoices')
    fee = models.ForeignKey(Fee, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    invoice_number = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    issued_at = models.DateField()
    status = models.CharField(max_length=20, default='ISSUED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'invoice_number')


class StudentAccount(models.Model):
    school = models.ForeignKey(
        'schools.School', on_delete=models.CASCADE, related_name='student_accounts'
    )
    student = models.OneToOneField(
        'students.Student', on_delete=models.CASCADE, related_name='account'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Account {self.student}'
