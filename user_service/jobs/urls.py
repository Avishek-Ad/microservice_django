from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.JobListAPIView.as_view(), name="job-list"),
    path('jobs/search/', views.JobSearchAPIView.as_view(), name="job-search"),
    path('apply/', views.ApplyJobAPIView.as_view(), name="apply-job"),
    path('generate-file-upload-path/', views.GeneratePresignedUrlView.as_view(), name="generate-file-upload-path")
]
