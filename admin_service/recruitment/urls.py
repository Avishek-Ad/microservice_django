from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.PublicAdminJobListAPIView.as_view())
]
