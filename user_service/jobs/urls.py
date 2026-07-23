from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.JobListAPIView.as_view(), name="job-list"),
    path('jobs/search/', views.JobSearchAPIView.as_view(), name="job-search"),
    path('apply/', views.ApplyJobAPIView.as_view(), name="apply-job")
]
