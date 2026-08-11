from django.urls import path

from .views import (
    BirthProfileListCreateView,
    NatalChartCreateView,
    NatalChartDetailView,
    NatalChartListView,
)

urlpatterns = [
    path("birth-profiles/", BirthProfileListCreateView.as_view(), name="birth-profile-list-create"),
    path("charts/", NatalChartListView.as_view(), name="chart-list"),
    path("charts/create/", NatalChartCreateView.as_view(), name="chart-create"),
    path("charts/<uuid:pk>/", NatalChartDetailView.as_view(), name="chart-detail"),
]
