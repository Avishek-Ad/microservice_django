from django.urls import path
from . import views

urlpatterns = [
    path("logs/", views.ListLogAPIView.as_view())
]
