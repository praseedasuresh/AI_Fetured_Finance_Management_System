from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.report_dashboard, name='report_dashboard'),
    
    # Report Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/update/', views.template_update, name='template_update'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    
    # Saved Reports
    path('saved/', views.saved_report_list, name='saved_report_list'),
    path('saved/<int:pk>/', views.saved_report_detail, name='saved_report_detail'),
    path('saved/<int:pk>/delete/', views.saved_report_delete, name='saved_report_delete'),
    path('saved/<int:pk>/download/', views.saved_report_download, name='saved_report_download'),
    
    # Scheduled Reports
    path('scheduled/', views.scheduled_report_list, name='scheduled_report_list'),
    path('scheduled/create/', views.scheduled_report_create, name='scheduled_report_create'),
    path('scheduled/<int:pk>/update/', views.scheduled_report_update, name='scheduled_report_update'),
    path('scheduled/<int:pk>/delete/', views.scheduled_report_delete, name='scheduled_report_delete'),
    path('scheduled/<int:pk>/toggle-active/', views.scheduled_report_toggle_active, name='scheduled_report_toggle_active'),
    path('scheduled/<int:pk>/run-now/', views.scheduled_report_run_now, name='scheduled_report_run_now'),
    
    # Report Generation
    path('generate/', views.generate_report, name='generate_report'),
]
