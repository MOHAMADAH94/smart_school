from rest_framework import serializers

from .models import Expense, Fee, Invoice, Payment, StudentAccount


class FeeSerializer(serializers.ModelSerializer):
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Fee
        fields = (
            'id',
            'student',
            'student_name',
            'title',
            'academic_year',
            'amount',
            'paid_amount',
            'remaining_amount',
            'due_date',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'paid_amount',
            'remaining_amount',
            'student_name',
        )

    def get_paid_amount(self, obj):
        return obj.paid_amount

    def get_remaining_amount(self, obj):
        return obj.remaining_amount

    def validate_student(self, student):
        if student.school_id != self.context['request'].school.id:
            raise serializers.ValidationError('الطالب لا ينتمي إلى هذه المدرسة.')
        return student


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'fee',
            'student',
            'student_name',
            'amount',
            'payment_date',
            'method',
            'reference',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'student_name')

    def validate(self, attrs):
        school = self.context['request'].school
        fee = attrs.get('fee') or getattr(self.instance, 'fee', None)
        student = attrs.get('student') or getattr(self.instance, 'student', None)
        if fee and fee.school_id != school.id:
            raise serializers.ValidationError({'fee': 'الرسوم لا تنتمي إلى هذه المدرسة.'})
        if student and student.school_id != school.id:
            raise serializers.ValidationError({'student': 'الطالب لا ينتمي إلى هذه المدرسة.'})
        if fee and student and fee.student_id != student.id:
            raise serializers.ValidationError({'student': 'الطالب لا يطابق رسوم الفاتورة.'})
        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = (
            'id',
            'title',
            'category',
            'amount',
            'expense_date',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            'id',
            'student',
            'fee',
            'invoice_number',
            'amount',
            'issued_at',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class StudentAccountSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = StudentAccount
        fields = ('id', 'student', 'student_name', 'balance', 'updated_at')
        read_only_fields = fields
