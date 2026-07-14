from django.urls import path
from . import views

urlpatterns = [
    path('posted_jobs/', views.PublicAdminJobListAPIView.as_view())
]
