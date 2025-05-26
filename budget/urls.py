from django.urls import path
from . import views

urlpatterns = [
    # Budget Dashboard
    path('dashboard/', views.budget_dashboard, name='budget_dashboard'),
    
    # Budget Categories
    path('categories/', views.budget_category_list, name='budget_category_list'),
    path('categories/create/', views.budget_category_create, name='budget_category_create'),
    path('categories/<int:pk>/update/', views.budget_category_update, name='budget_category_update'),
    path('categories/<int:pk>/delete/', views.budget_category_delete, name='budget_category_delete'),
    
    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('budgets/<int:pk>/update/', views.budget_update, name='budget_update'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    path('budgets/<int:pk>/approve/', views.budget_approval, name='budget_approval'),
    path('budgets/export-csv/', views.export_budget_csv, name='export_budget_csv'),
    
    # Budget Allocations
    path('allocations/', views.budget_allocation_list, name='budget_allocation_list'),
    path('allocations/create/', views.budget_allocation_create, name='budget_allocation_create'),
    path('allocations/<int:pk>/update/', views.budget_allocation_update, name='budget_allocation_update'),
    path('allocations/<int:pk>/delete/', views.budget_allocation_delete, name='budget_allocation_delete'),
    path('allocations/export-csv/', views.export_allocations_csv, name='export_allocations_csv'),
    
    # Budget Transfers
    path('transfers/', views.budget_transfer_list, name='budget_transfer_list'),
    path('transfers/create/', views.budget_transfer_create, name='budget_transfer_create'),
    path('transfers/<int:pk>/update/', views.budget_transfer_update, name='budget_transfer_update'),
    path('transfers/<int:pk>/delete/', views.budget_transfer_delete, name='budget_transfer_delete'),
    path('transfers/<int:pk>/approve/', views.budget_transfer_approval, name='budget_transfer_approval'),
    path('transfers/export-csv/', views.export_transfers_csv, name='export_transfers_csv'),
    
    # Budget Predictions (AI Feature)
    path('predictions/', views.budget_prediction_list, name='budget_prediction_list'),
    path('predictions/create/', views.budget_prediction_create, name='budget_prediction_create'),
    path('predictions/<int:pk>/', views.budget_prediction_detail, name='budget_prediction_detail'),
    path('predictions/<int:pk>/apply/', views.budget_prediction_apply, name='budget_prediction_apply'),
    path('predictions/<int:pk>/delete/', views.budget_prediction_delete, name='budget_prediction_delete'),
    path('predictions/export-csv/', views.export_predictions_csv, name='export_predictions_csv'),
    
    # API Endpoints
    path('api/budget/<int:budget_id>/', views.api_get_budget_details, name='api_budget_details'),
]
