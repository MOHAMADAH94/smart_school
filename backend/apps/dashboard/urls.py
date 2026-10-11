from django.urls import path

from .views import DashboardSectionView, DashboardStatsView, SmartInsightsView

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('insights/', SmartInsightsView.as_view(), name='dashboard-insights'),
    path('sections/<str:section>/', DashboardSectionView.as_view(), name='dashboard-section'),
]
