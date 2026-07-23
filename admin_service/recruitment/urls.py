from django.urls import path
from . import views

urlpatterns = [
    path('posted_jobs/', views.PublicAdminJobListAPIView.as_view(), name="public-admin-job-list"),
    path('jobs/', views.JobListCreateAPIView.as_view(), name="job-list-create"),
    path('jobs/<int:pk>/', views.JobRetriveUpdateAPIView.as_view(), name="job-detail"),
    path('jobs/<int:pk>/delete/', views.JobDeleteThroughPostAPIView.as_view(), name="job-delete-through-post"),
    path('jobs/<int:job_id>/applications/', views.JobApplicationsListAPIView.as_view(), name="job-applications-list"),
    path('jobs/<int:job_id>/applications/<int:user_app_id>/', views.JobApplicationsStatusChange.as_view(), name="job-status-change")
]
