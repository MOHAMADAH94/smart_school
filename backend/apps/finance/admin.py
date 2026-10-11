from django.contrib import admin

from .models import Expense, Fee, Invoice, Payment, StudentAccount


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'amount', 'school')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'payment_date', 'school')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'expense_date', 'school')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'student', 'amount', 'status', 'school')


@admin.register(StudentAccount)
class StudentAccountAdmin(admin.ModelAdmin):
    list_display = ('student', 'balance', 'school')
