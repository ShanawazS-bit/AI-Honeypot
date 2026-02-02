from django.urls import path
from .views import HoneypotEndpoint

urlpatterns = [
    path('chat', HoneypotEndpoint.as_view(), name='honeypot-chat'),
]
