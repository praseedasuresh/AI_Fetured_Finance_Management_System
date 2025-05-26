from django.urls import path
from . import views

urlpatterns = [
    # Fee Dashboard
    path('dashboard/', views.fee_dashboard, name='fee_dashboard'),
    
    # Fee Categories
    path('categories/', views.fee_category_list, name='fee_category_list'),
    path('categories/create/', views.fee_category_create, name='fee_category_create'),
    path('categories/<int:pk>/update/', views.fee_category_update, name='fee_category_update'),
    path('categories/<int:pk>/delete/', views.fee_category_delete, name='fee_category_delete'),
    
    # Fee Structures
    path('structures/', views.fee_structure_list, name='fee_structure_list'),
    path('structures/create/', views.fee_structure_create, name='fee_structure_create'),
    path('structures/<int:pk>/update/', views.fee_structure_update, name='fee_structure_update'),
    path('structures/<int:pk>/delete/', views.fee_structure_delete, name='fee_structure_delete'),
    
    # Student Fees
    path('student-fees/', views.student_fee_list, name='student_fee_list'),
    path('student-fees/create/', views.student_fee_create, name='student_fee_create'),
    path('student-fees/<int:pk>/update/', views.student_fee_update, name='student_fee_update'),
    path('student-fees/<int:pk>/delete/', views.student_fee_delete, name='student_fee_delete'),
    path('student-fees/bulk-assignment/', views.bulk_fee_assignment, name='bulk_fee_assignment'),
    
    # Fee Payments
    path('payments/', views.fee_payment_list, name='fee_payment_list'),
    path('payments/create/', views.fee_payment_create, name='fee_payment_create'),
    path('payments/<int:pk>/update/', views.fee_payment_update, name='fee_payment_update'),
    path('payments/<int:pk>/delete/', views.fee_payment_delete, name='fee_payment_delete'),
    path('payments/export-csv/', views.export_payments_csv, name='export_payments_csv'),
    
    # Student Fee Views (for students)
    path('my-fees/', views.student_fee_history, name='student_fee_history'),
    
    # API Endpoints
    path('api/student-fees/<int:student_id>/', views.student_fees_api, name='student_fees_api'),
]
