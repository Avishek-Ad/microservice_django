from django.urls import path
from . import views

urlpatterns = [
    path('posted_jobs/', views.PublicAdminJobListAPIView.as_view()),
    path('jobs/', views.JobListCreateAPIView.as_view()),
    path('jobs/<job_id:int>/', views.JobRetriveUpdateDestroyAPIView.as_view()),
    path('jobs/<job_id:int>/applications/', views.JobApplicationsListAPIView.as_view()),
    path('jobs/<job_id:int>/applications/<user_app_id:int>/', views.JobApplicationsStatusChange.as_view())
]
