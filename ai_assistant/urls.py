from django.urls import path
from . import views

urlpatterns = [
    # Chat dashboard
    path('dashboard/', views.chat_dashboard, name='ai_dashboard'),
    
    # Chat sessions
    path('chat/', views.chat_session, name='new_chat_session'),
    path('chat/<int:session_id>/', views.chat_session, name='chat_session'),
    
    # API endpoints
    path('api/chat/<int:session_id>/message/', views.chat_message_api, name='chat_message_api'),
    
    # Anomaly detection
    path('anomalies/', views.anomaly_detection_dashboard, name='anomaly_dashboard'),
    path('anomalies/<int:anomaly_id>/', views.anomaly_detail, name='anomaly_detail'),
    path('anomalies/run/', views.run_anomaly_detection, name='run_anomaly_detection'),
]
