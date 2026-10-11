from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MySubscriptionView, PlanListView, SubscriptionPaymentViewSet

router = DefaultRouter()
router.register(r'payments', SubscriptionPaymentViewSet, basename='subscription-payment')

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='subscription-plans'),
    path('me/', MySubscriptionView.as_view(), name='subscription-me'),
    path('', include(router.urls)),
]
