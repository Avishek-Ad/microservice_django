from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.JobListAPIView.as_view()),
    path('apply/', views.ApplyJobAPIView.as_view())
]
