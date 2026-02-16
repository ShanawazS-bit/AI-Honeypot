from django.urls import path
from .views import HoneypotEndpoint, CallSessionView, CallReportView

urlpatterns = [
    path('chat', HoneypotEndpoint.as_view(), name='honeypot-chat'),
    path('session/start', CallSessionView.as_view(), name='session-start'),
    path('report/<str:session_id>', CallReportView.as_view(), name='call-report'),
]
