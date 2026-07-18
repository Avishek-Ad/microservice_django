from django.urls import path
from . import views

urlpatterns = [
    path('posted_jobs/', views.PublicAdminJobListAPIView.as_view()),
    path('jobs/', views.JobListCreateAPIView.as_view()),
    path('jobs/<int:pk>/', views.JobRetriveUpdateDestroyAPIView.as_view()),
    path('jobs/<int:job_id>/applications/', views.JobApplicationsListAPIView.as_view()),
    path('jobs/<int:job_id>/applications/<int:user_app_id>/', views.JobApplicationsStatusChange.as_view())
]
