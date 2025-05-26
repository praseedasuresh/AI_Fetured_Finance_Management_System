from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.expense_dashboard, name='expense_dashboard'),
    
    # Expense Categories
    path('categories/', views.expense_category_list, name='expense_category_list'),
    path('categories/create/', views.expense_category_create, name='expense_category_create'),
    path('categories/<int:pk>/update/', views.expense_category_update, name='expense_category_update'),
    path('categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),
    path('categories/export/csv/', views.export_expense_categories_csv, name='expense_category_export'),
    
    # Expenses
    path('list/', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/', views.expense_detail, name='expense_detail'),
    path('<int:pk>/update/', views.expense_update, name='expense_update'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('<int:pk>/approve/', views.expense_approval, name='expense_approval'),
    path('<int:pk>/payment/', views.expense_payment, name='expense_payment'),
    
    # Expense Attachments
    path('<int:pk>/attachments/add/', views.expense_add_attachment, name='expense_add_attachment'),
    path('<int:expense_pk>/attachments/<int:attachment_pk>/delete/', views.expense_delete_attachment, name='expense_delete_attachment'),
    
    # Export
    path('export/csv/', views.export_expenses_csv, name='export_expenses_csv'),
    
    # Recurring Expenses
    path('recurring/', views.recurring_expense_list, name='recurring_expense_list'),
    path('recurring/create/', views.recurring_expense_create, name='recurring_expense_create'),
    path('recurring/<int:pk>/update/', views.recurring_expense_update, name='recurring_expense_update'),
    path('recurring/<int:pk>/delete/', views.recurring_expense_delete, name='recurring_expense_delete'),
    path('recurring/<int:pk>/toggle-active/', views.recurring_expense_toggle_active, name='recurring_expense_toggle_active'),
    path('recurring/<int:pk>/create-now/', views.recurring_expense_create_now, name='recurring_expense_create_now'),
    path('recurring/export/csv/', views.export_recurring_expense_csv, name='export_recurring_expense_csv'),
]
