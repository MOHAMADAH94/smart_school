from django.urls import path

from .views import CreateSchoolView, CurrentContextView, MySchoolsView, SchoolDetailView

urlpatterns = [
    path('', MySchoolsView.as_view(), name='schools-list'),
    path('create/', CreateSchoolView.as_view(), name='schools-create'),
    path('current/', CurrentContextView.as_view(), name='schools-current'),
    path('me/', SchoolDetailView.as_view(), name='schools-me'),
]
