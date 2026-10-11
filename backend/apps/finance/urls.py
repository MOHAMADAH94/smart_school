from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExpenseViewSet, FeeViewSet, InvoiceViewSet, PaymentViewSet, StudentAccountViewSet

router = DefaultRouter()
router.register(r'fees', FeeViewSet, basename='fee')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'accounts', StudentAccountViewSet, basename='student-account')

urlpatterns = [
    path('', include(router.urls)),
]
