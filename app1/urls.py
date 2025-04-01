from django.urls import path
from app1.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name="home")
]
