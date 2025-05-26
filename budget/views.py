from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import csv
import datetime

from .models import BudgetCategory, Budget, BudgetAllocation, BudgetTransfer, BudgetPrediction
from .forms import (
    BudgetCategoryForm, BudgetForm, BudgetApprovalForm, BudgetAllocationForm,
    BudgetTransferForm, BudgetTransferApprovalForm, BudgetSearchForm,
    BudgetPredictionForm, BudgetPredictionApplyForm
)
from users.decorators import admin_required, finance_staff_required
from core.models import AcademicYear, Department


@finance_staff_required
def budget_dashboard(request):
    """Dashboard view for budget management"""
    # Get current academic year
    current_year = AcademicYear.get_active()
    
    # Get budget statistics
    total_budget = Budget.objects.filter(
        academic_year=current_year,
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Get budget allocations
    total_allocated = BudgetAllocation.objects.filter(
        budget__academic_year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate remaining budget
    remaining_budget = total_budget - total_allocated
    
    # Get department-wise budget distribution
    department_budgets = Budget.objects.filter(
        academic_year=current_year,
        status='approved'
    ).values('department__name').annotate(total=Sum('amount')).order_by('-total')
    
    # Get recent budget allocations
    recent_allocations = BudgetAllocation.objects.filter(
        budget__academic_year=current_year
    ).order_by('-allocated_date')[:10]
    
    # Get pending budget approvals
    pending_approvals = Budget.objects.filter(status='submitted').order_by('-created_at')[:10]
    
    # Get pending budget transfers
    pending_transfers = BudgetTransfer.objects.filter(approved=False).order_by('-transfer_date')[:10]
    
    # Get budget categories
    budget_categories = BudgetCategory.objects.all()
    
    context = {
        'total_budget': total_budget,
        'total_allocated': total_allocated,
        'remaining_budget': remaining_budget,
        'utilization_percentage': (total_allocated / total_budget * 100) if total_budget > 0 else 0,
        'department_budgets': department_budgets,
        'recent_allocations': recent_allocations,
        'pending_approvals': pending_approvals,
        'pending_transfers': pending_transfers,
        'current_year': current_year,
        'categories': budget_categories,
    }
    
    return render(request, 'budget/dashboard.html', context)


# Budget Category Views
@finance_staff_required
def budget_category_list(request):
    """View for listing budget categories"""
    categories = BudgetCategory.objects.all()
    return render(request, 'budget/category/list.html', {'categories': categories})


@finance_staff_required
def budget_category_create(request):
    """View for creating a new budget category"""
    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget category created successfully!')
            return redirect('budget_category_list')
    else:
        form = BudgetCategoryForm()
    
    return render(request, 'budget/category/form.html', {'form': form, 'title': 'Create Budget Category'})


@finance_staff_required
def budget_category_update(request, pk):
    """View for updating a budget category"""
    category = get_object_or_404(BudgetCategory, pk=pk)
    
    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget category updated successfully!')
            return redirect('budget_category_list')
    else:
        form = BudgetCategoryForm(instance=category)
    
    return render(request, 'budget/category/form.html', {'form': form, 'title': 'Update Budget Category'})


@finance_staff_required
def budget_category_delete(request, pk):
    """View for deleting a budget category"""
    category = get_object_or_404(BudgetCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, 'Budget category deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting budget category: {str(e)}')
        return redirect('budget_category_list')
    
    return render(request, 'budget/category/delete.html', {'category': category})


# Budget Views
@finance_staff_required
def budget_list(request):
    """View for listing budgets"""
    # Get all budgets without any filtering initially
    budgets = Budget.objects.all().select_related('department', 'academic_year', 'category')
    
    # Check if we have any budgets at all
    total_budgets = budgets.count()
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        budgets = budgets.filter(
            Q(title__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply form filters if the form is valid
    form = BudgetSearchForm(request.GET)
    if form.is_valid():
        department = form.cleaned_data.get('department')
        academic_year = form.cleaned_data.get('academic_year')
        category = form.cleaned_data.get('category')
        status = form.cleaned_data.get('status')
        
        if department:
            budgets = budgets.filter(department=department)
        
        if academic_year:
            budgets = budgets.filter(academic_year=academic_year)
        
        if category:
            budgets = budgets.filter(category=category)
        
        if status:
            budgets = budgets.filter(status=status)
    
    # Order the results
    budgets = budgets.order_by('-created_at')
    
    # Paginate the results
    paginator = Paginator(budgets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add debug message if no budgets are found
    if total_budgets == 0:
        messages.info(request, 'No budgets found in the database. Create your first budget by clicking the "Add Budget" button above.')
    
    return render(request, 'budget/budget/list.html', {
        'page_obj': page_obj,
        'form': form,
        'total_budgets': total_budgets
    })


@finance_staff_required
def budget_create(request):
    """View for creating a new budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            try:
                budget = form.save(commit=False)
                budget.submitted_by = request.user
                budget.save()
                
                messages.success(request, 'Budget created successfully!')
                return redirect('budget_list')
            except Exception as e:
                messages.error(request, f'Error creating budget: {str(e)}')
        else:
            # Form is invalid, display errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Pre-fill academic year with active year
        initial = {'academic_year': AcademicYear.get_active()}
        form = BudgetForm(initial=initial)
    
    return render(request, 'budget/budget/form.html', {'form': form, 'title': 'Create Budget'})


@finance_staff_required
def budget_update(request, pk):
    """View for updating a budget"""
    budget = get_object_or_404(Budget, pk=pk)
    
    # Only allow updates if budget is in draft or rejected status
    if budget.status not in ['draft', 'rejected']:
        messages.error(request, 'You can only edit budgets in draft or rejected status.')
        return redirect('budget_list')
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated successfully!')
            return redirect('budget_list')
    else:
        form = BudgetForm(instance=budget)
    
    return render(request, 'budget/budget/form.html', {'form': form, 'title': 'Update Budget'})


@finance_staff_required
def budget_delete(request, pk):
    """View for deleting a budget"""
    budget = get_object_or_404(Budget, pk=pk)
    
    # Only allow deletion if budget is in draft or rejected status
    if budget.status not in ['draft', 'rejected']:
        messages.error(request, 'You can only delete budgets in draft or rejected status.')
        return redirect('budget_list')
    
    if request.method == 'POST':
        try:
            budget.delete()
            messages.success(request, 'Budget deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting budget: {str(e)}')
        return redirect('budget_list')
    
    return render(request, 'budget/budget/delete.html', {'budget': budget})


@finance_staff_required
def budget_detail(request, pk):
    """View for viewing budget details"""
    budget = get_object_or_404(Budget, pk=pk)
    
    # Get allocations for this budget
    allocations = BudgetAllocation.objects.filter(budget=budget).order_by('-allocated_date')
    
    # Calculate total allocated
    total_allocated = allocations.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get transfers for this budget
    transfers_from = BudgetTransfer.objects.filter(from_budget=budget, approved=True).order_by('-transfer_date')
    transfers_to = BudgetTransfer.objects.filter(to_budget=budget, approved=True).order_by('-transfer_date')
    
    # Calculate total transfers
    total_transfers_out = transfers_from.aggregate(total=Sum('amount'))['total'] or 0
    total_transfers_in = transfers_to.aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate remaining budget
    remaining_budget = budget.amount - total_allocated - total_transfers_out + total_transfers_in
    
    context = {
        'budget': budget,
        'allocations': allocations,
        'transfers_from': transfers_from,
        'transfers_to': transfers_to,
        'total_allocated': total_allocated,
        'total_transfers_out': total_transfers_out,
        'total_transfers_in': total_transfers_in,
        'remaining_budget': remaining_budget,
        'utilization_percentage': (total_allocated / budget.amount * 100) if budget.amount > 0 else 0,
    }
    
    return render(request, 'budget/budget/detail.html', context)


@admin_required
def budget_approval(request, pk):
    """View for approving or rejecting budgets"""
    budget = get_object_or_404(Budget, pk=pk)
    
    # Only allow approval if budget is in submitted status
    if budget.status != 'submitted':
        messages.error(request, 'You can only approve budgets in submitted status.')
        return redirect('budget_list')
    
    if request.method == 'POST':
        form = BudgetApprovalForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data.get('decision')
            rejection_reason = form.cleaned_data.get('rejection_reason')
            
            if decision == 'approve':
                budget.approve(request.user)
                messages.success(request, 'Budget approved successfully!')
            else:
                budget.reject(rejection_reason)
                messages.success(request, 'Budget rejected successfully!')
            
            return redirect('budget_list')
    else:
        form = BudgetApprovalForm()
    
    return render(request, 'budget/budget/approval.html', {'form': form, 'budget': budget})


# Budget Allocation Views
@finance_staff_required
def budget_allocation_list(request):
    """View for listing budget allocations"""
    allocations = BudgetAllocation.objects.all().order_by('-allocated_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            allocations = allocations.filter(allocated_date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    paginator = Paginator(allocations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'budget/allocation/list.html', {'page_obj': page_obj})


@finance_staff_required
def budget_allocation_create(request):
    """View for creating a new budget allocation"""
    if request.method == 'POST':
        form = BudgetAllocationForm(request.POST)
        if form.is_valid():
            allocation = form.save(commit=False)
            allocation.allocated_by = request.user
            allocation.save()
            
            messages.success(request, 'Budget allocation created successfully!')
            return redirect('budget_allocation_list')
    else:
        form = BudgetAllocationForm()
    
    return render(request, 'budget/allocation/form.html', {'form': form, 'title': 'Create Budget Allocation'})


@finance_staff_required
def budget_allocation_update(request, pk):
    """View for updating a budget allocation"""
    allocation = get_object_or_404(BudgetAllocation, pk=pk)
    
    if request.method == 'POST':
        form = BudgetAllocationForm(request.POST, instance=allocation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget allocation updated successfully!')
            return redirect('budget_allocation_list')
    else:
        form = BudgetAllocationForm(instance=allocation)
    
    return render(request, 'budget/allocation/form.html', {'form': form, 'title': 'Update Budget Allocation'})


@finance_staff_required
def budget_allocation_delete(request, pk):
    """View for deleting a budget allocation"""
    allocation = get_object_or_404(BudgetAllocation, pk=pk)
    
    if request.method == 'POST':
        try:
            allocation.delete()
            messages.success(request, 'Budget allocation deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting budget allocation: {str(e)}')
        return redirect('budget_allocation_list')
    
    return render(request, 'budget/allocation/delete.html', {'allocation': allocation})


# Budget Transfer Views
@finance_staff_required
def budget_transfer_list(request):
    """View for listing budget transfers"""
    transfers = BudgetTransfer.objects.all().order_by('-transfer_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            transfers = transfers.filter(transfer_date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'budget/transfer/list.html', {'page_obj': page_obj})


@finance_staff_required
def budget_transfer_create(request):
    """View for creating a new budget transfer"""
    if request.method == 'POST':
        form = BudgetTransferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget transfer request created successfully!')
            return redirect('budget_transfer_list')
    else:
        form = BudgetTransferForm()
    
    return render(request, 'budget/transfer/form.html', {'form': form, 'title': 'Create Budget Transfer'})


@finance_staff_required
def budget_transfer_update(request, pk):
    """View for updating a budget transfer"""
    transfer = get_object_or_404(BudgetTransfer, pk=pk)
    
    # Only allow updates if transfer is not approved
    if transfer.approved:
        messages.error(request, 'You cannot edit an approved transfer.')
        return redirect('budget_transfer_list')
    
    if request.method == 'POST':
        form = BudgetTransferForm(request.POST, instance=transfer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget transfer updated successfully!')
            return redirect('budget_transfer_list')
    else:
        form = BudgetTransferForm(instance=transfer)
    
    return render(request, 'budget/transfer/form.html', {'form': form, 'title': 'Update Budget Transfer'})


@finance_staff_required
def budget_transfer_delete(request, pk):
    """View for deleting a budget transfer"""
    transfer = get_object_or_404(BudgetTransfer, pk=pk)
    
    # Only allow deletion if transfer is not approved
    if transfer.approved:
        messages.error(request, 'You cannot delete an approved transfer.')
        return redirect('budget_transfer_list')
    
    if request.method == 'POST':
        try:
            transfer.delete()
            messages.success(request, 'Budget transfer deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting budget transfer: {str(e)}')
        return redirect('budget_transfer_list')
    
    return render(request, 'budget/transfer/delete.html', {'transfer': transfer})


@admin_required
def budget_transfer_approval(request, pk):
    """View for approving budget transfers"""
    transfer = get_object_or_404(BudgetTransfer, pk=pk)
    
    # Only allow approval if transfer is not already approved
    if transfer.approved:
        messages.error(request, 'This transfer has already been approved.')
        return redirect('budget_transfer_list')
    
    if request.method == 'POST':
        form = BudgetTransferApprovalForm(request.POST)
        if form.is_valid():
            approve = form.cleaned_data.get('approve')
            
            if approve:
                transfer.approve(request.user)
                messages.success(request, 'Budget transfer approved successfully!')
            else:
                transfer.delete()
                messages.success(request, 'Budget transfer rejected and deleted successfully!')
            
            return redirect('budget_transfer_list')
    else:
        form = BudgetTransferApprovalForm()
    
    return render(request, 'budget/transfer/approval.html', {'form': form, 'transfer': transfer})


@finance_staff_required
def api_get_budget_details(request, budget_id):
    """API endpoint to get budget details for the budget transfer form"""
    try:
        budget = get_object_or_404(Budget, pk=budget_id)
        
        # Calculate total allocations
        total_allocations = BudgetAllocation.objects.filter(budget=budget).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate total transfers from this budget
        total_transfers_out = BudgetTransfer.objects.filter(from_budget=budget, approved=True).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate total transfers to this budget
        total_transfers_in = BudgetTransfer.objects.filter(to_budget=budget, approved=True).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate available amount
        available_amount = float(budget.amount) - float(total_allocations) - float(total_transfers_out) + float(total_transfers_in)
        
        # Return JSON response
        return JsonResponse({
            'id': budget.id,
            'title': budget.title,
            'department': budget.department.name,
            'amount': float(budget.amount),
            'available': available_amount,
            'status': budget.status
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@finance_staff_required
def export_budget_csv(request):
    """View for exporting budgets to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budgets.csv"'
    
    # Get filter parameters
    department_id = request.GET.get('department')
    academic_year_id = request.GET.get('academic_year')
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    
    budgets = Budget.objects.all()
    
    if department_id:
        budgets = budgets.filter(department_id=department_id)
    
    if academic_year_id:
        budgets = budgets.filter(academic_year_id=academic_year_id)
    
    if category_id:
        budgets = budgets.filter(category_id=category_id)
    
    if status:
        budgets = budgets.filter(status=status)
    
    writer = csv.writer(response)
    writer.writerow([
        'Title', 'Department', 'Academic Year', 'Category', 'Amount',
        'Status', 'Submitted By', 'Approved By', 'Approved Date'
    ])
    
    for budget in budgets:
        writer.writerow([
            budget.title,
            budget.department.name,
            budget.academic_year.name,
            budget.category.name,
            budget.amount,
            budget.get_status_display(),
            budget.submitted_by.get_full_name() if budget.submitted_by else '',
            budget.approved_by.get_full_name() if budget.approved_by else '',
            budget.approved_date.strftime('%Y-%m-%d %H:%M') if budget.approved_date else ''
        ])
    
    return response


@finance_staff_required
def export_allocations_csv(request):
    """View for exporting budget allocations to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budget_allocations.csv"'
    
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    allocations = BudgetAllocation.objects.all().order_by('-allocated_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            allocations = allocations.filter(allocated_date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    writer = csv.writer(response)
    writer.writerow([
        'Budget', 'Department', 'Academic Year', 'Title', 'Amount',
        'Allocation Date', 'Allocated By'
    ])
    
    for allocation in allocations:
        writer.writerow([
            allocation.budget.title,
            allocation.budget.department.name,
            allocation.budget.academic_year.name,
            allocation.title,
            allocation.amount,
            allocation.allocated_date.strftime('%Y-%m-%d'),
            allocation.allocated_by.get_full_name() if allocation.allocated_by else ''
        ])
    
    return response


@finance_staff_required
def export_transfers_csv(request):
    """View for exporting budget transfers to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budget_transfers.csv"'
    
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    transfers = BudgetTransfer.objects.all().order_by('-transfer_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            transfers = transfers.filter(transfer_date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    writer = csv.writer(response)
    writer.writerow([
        'From Budget', 'To Budget', 'Amount', 'Transfer Date', 
        'Reason', 'Status', 'Approved By', 'Approval Date'
    ])
    
    for transfer in transfers:
        writer.writerow([
            transfer.from_budget.title,
            transfer.to_budget.title,
            transfer.amount,
            transfer.transfer_date.strftime('%Y-%m-%d'),
            transfer.reason,
            'Approved' if transfer.approved else 'Pending',
            transfer.approved_by.get_full_name() if transfer.approved_by else '',
            transfer.approval_date.strftime('%Y-%m-%d') if transfer.approval_date else ''
        ])
    
    return response


# Budget Prediction Views
@finance_staff_required
def budget_prediction_list(request):
    """View for listing budget predictions"""
    predictions = BudgetPrediction.objects.all().order_by('-created_at')
    
    # Apply filters if provided
    if request.GET.get('department'):
        department = request.GET.get('department')
        predictions = predictions.filter(department__id=department)
    
    if request.GET.get('academic_year'):
        academic_year = request.GET.get('academic_year')
        predictions = predictions.filter(academic_year__id=academic_year)
    
    if request.GET.get('category'):
        category = request.GET.get('category')
        predictions = predictions.filter(category__id=category)
    
    if request.GET.get('is_applied') == 'yes':
        predictions = predictions.filter(is_applied=True)
    elif request.GET.get('is_applied') == 'no':
        predictions = predictions.filter(is_applied=False)
    
    # Pagination
    paginator = Paginator(predictions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'departments': Department.objects.all(),
        'academic_years': AcademicYear.objects.all(),
        'categories': BudgetCategory.objects.all(),
    }
    
    return render(request, 'budget/prediction_list.html', context)


@finance_staff_required
def budget_prediction_create(request):
    """View for creating a new budget prediction using AI"""
    if request.method == 'POST':
        form = BudgetPredictionForm(request.POST)
        if form.is_valid():
            department = form.cleaned_data['department']
            academic_year = form.cleaned_data['academic_year']
            category = form.cleaned_data['category']
            include_previous_years = form.cleaned_data['include_previous_years']
            include_expense_trends = form.cleaned_data['include_expense_trends']
            include_department_growth = form.cleaned_data['include_department_growth']
            
            # Check if prediction already exists
            existing_prediction = BudgetPrediction.objects.filter(
                department=department,
                academic_year=academic_year,
                category=category
            ).first()
            
            if existing_prediction:
                messages.warning(request, f'A prediction already exists for {department.name}, {academic_year.name}, {category.name}. Please view or delete it first.')
                return redirect('budget_prediction_detail', pk=existing_prediction.pk)
            
            # Generate prediction using AI algorithm
            prediction_data = generate_budget_prediction(
                department, 
                academic_year, 
                category,
                include_previous_years,
                include_expense_trends,
                include_department_growth
            )
            
            # Create prediction record
            prediction = BudgetPrediction.objects.create(
                department=department,
                academic_year=academic_year,
                category=category,
                predicted_amount=prediction_data['predicted_amount'],
                confidence_score=prediction_data['confidence_score'],
                factors=prediction_data['factors'],
                created_by=request.user
            )
            
            messages.success(request, f'Budget prediction created successfully with {prediction.confidence_score:.2%} confidence.')
            return redirect('budget_prediction_detail', pk=prediction.pk)
    else:
        form = BudgetPredictionForm()
    
    context = {
        'form': form,
        'title': 'Create Budget Prediction'
    }
    
    return render(request, 'budget/prediction_form.html', context)


@finance_staff_required
def budget_prediction_detail(request, pk):
    """View for viewing budget prediction details"""
    prediction = get_object_or_404(BudgetPrediction, pk=pk)
    
    # Get actual budget if prediction has been applied
    applied_budget = None
    if prediction.is_applied:
        applied_budget = Budget.objects.filter(
            department=prediction.department,
            academic_year=prediction.academic_year,
            category=prediction.category,
            description__contains='AI prediction'
        ).first()
    
    # Get historical data for comparison
    historical_budgets = Budget.objects.filter(
        department=prediction.department,
        category=prediction.category
    ).exclude(academic_year=prediction.academic_year).order_by('-academic_year__start_date')[:3]
    
    context = {
        'prediction': prediction,
        'applied_budget': applied_budget,
        'historical_budgets': historical_budgets,
        'apply_form': BudgetPredictionApplyForm(prediction=prediction),
        'factors': prediction.factors
    }
    
    return render(request, 'budget/prediction_detail.html', context)


@finance_staff_required
def budget_prediction_apply(request, pk):
    """View for applying a budget prediction to create an actual budget"""
    prediction = get_object_or_404(BudgetPrediction, pk=pk)
    
    if prediction.is_applied:
        messages.warning(request, 'This prediction has already been applied to create a budget.')
        return redirect('budget_prediction_detail', pk=prediction.pk)
    
    if request.method == 'POST':
        form = BudgetPredictionApplyForm(request.POST, prediction=prediction)
        if form.is_valid():
            # Get adjusted amount if provided
            adjusted_amount = form.cleaned_data.get('adjust_amount')
            if adjusted_amount:
                prediction.predicted_amount = adjusted_amount
            
            # Apply prediction to create budget
            budget = prediction.apply_prediction(request.user)
            
            if budget:
                messages.success(request, f'Budget created successfully based on the prediction: {budget.title}')
                return redirect('budget_detail', pk=budget.pk)
            else:
                messages.error(request, 'Failed to create budget from prediction.')
    
    return redirect('budget_prediction_detail', pk=prediction.pk)


@finance_staff_required
def budget_prediction_delete(request, pk):
    """View for deleting a budget prediction"""
    prediction = get_object_or_404(BudgetPrediction, pk=pk)
    
    if request.method == 'POST':
        prediction.delete()
        messages.success(request, 'Budget prediction deleted successfully.')
        return redirect('budget_prediction_list')
    
    context = {
        'prediction': prediction,
        'title': 'Delete Budget Prediction'
    }
    
    return render(request, 'budget/prediction_delete.html', context)


@finance_staff_required
def export_predictions_csv(request):
    """Export budget predictions to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budget_predictions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Department', 'Academic Year', 'Category', 'Predicted Amount', 
                    'Confidence Score', 'Applied', 'Created By', 'Created At'])
    
    predictions = BudgetPrediction.objects.all().order_by('-created_at')
    
    # Apply filters if provided
    if request.GET.get('department'):
        department = request.GET.get('department')
        predictions = predictions.filter(department__id=department)
    
    if request.GET.get('academic_year'):
        academic_year = request.GET.get('academic_year')
        predictions = predictions.filter(academic_year__id=academic_year)
    
    if request.GET.get('category'):
        category = request.GET.get('category')
        predictions = predictions.filter(category__id=category)
    
    for prediction in predictions:
        writer.writerow([
            prediction.department.name,
            prediction.academic_year.name,
            prediction.category.name,
            prediction.predicted_amount,
            f"{prediction.confidence_score:.2%}",
            'Yes' if prediction.is_applied else 'No',
            prediction.created_by.get_full_name() if prediction.created_by else '',
            prediction.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response


# AI Budget Prediction Algorithm
def generate_budget_prediction(department, academic_year, category, 
                              include_previous_years=True, 
                              include_expense_trends=True,
                              include_department_growth=True):
    """
    Generate a budget prediction using AI algorithms
    
    This function analyzes historical budget data, expense patterns, and department growth
    to predict an optimal budget allocation for the specified department, academic year,
    and category.
    """
    import numpy as np
    from sklearn.linear_model import LinearRegression
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize prediction data
        prediction_data = {
            'predicted_amount': 0,
            'confidence_score': 0,
            'factors': {
                'historical_data': {},
                'expense_trends': {},
                'department_growth': {},
                'inflation_adjustment': {},
                'prediction_details': {}
            }
        }
        
        # Get historical budget data for this department and category
        historical_budgets = []
        historical_years = []
        
        if include_previous_years:
            # Get previous budgets for this department and category
            previous_budgets = Budget.objects.filter(
                department=department,
                category=category,
                status='approved'  # Only consider approved budgets
            ).exclude(academic_year=academic_year).order_by('academic_year__start_date')
            
            for budget in previous_budgets:
                year_index = (budget.academic_year.start_date.year - 
                             AcademicYear.objects.earliest('start_date').start_date.year)
                historical_budgets.append(float(budget.amount))
                historical_years.append(year_index)
                
                # Store in factors for transparency
                prediction_data['factors']['historical_data'][budget.academic_year.name] = float(budget.amount)
        
        # If we have enough historical data, use linear regression
        if len(historical_budgets) >= 2:
            # Prepare data for regression
            X = np.array(historical_years).reshape(-1, 1)
            y = np.array(historical_budgets)
            
            # Fit linear regression model
            model = LinearRegression()
            model.fit(X, y)
            
            # Get current year index for prediction
            current_year_index = academic_year.start_date.year - AcademicYear.objects.earliest('start_date').start_date.year
            
            # Predict amount
            base_prediction = model.predict([[current_year_index]])[0]
            
            # Store regression details
            prediction_data['factors']['prediction_details']['regression_coefficient'] = float(model.coef_[0])
            prediction_data['factors']['prediction_details']['regression_intercept'] = float(model.intercept_)
            prediction_data['factors']['prediction_details']['base_prediction'] = float(base_prediction)
            
            # Set initial prediction and confidence
            prediction_data['predicted_amount'] = base_prediction
            prediction_data['confidence_score'] = min(0.7, 0.5 + (len(historical_budgets) * 0.05))
            
        else:
            # Not enough historical data, use average of similar departments or default amount
            similar_budgets = Budget.objects.filter(
                category=category,
                academic_year=academic_year,
                status='approved'
            ).exclude(department=department)
            
            if similar_budgets.exists():
                avg_amount = similar_budgets.aggregate(avg=Sum('amount') / similar_budgets.count())['avg'] or 0
                prediction_data['predicted_amount'] = avg_amount
                prediction_data['confidence_score'] = 0.4
                prediction_data['factors']['prediction_details']['method'] = 'similar_departments_average'
                prediction_data['factors']['prediction_details']['similar_departments_count'] = similar_budgets.count()
            else:
                # Use last year's budget for this department if available
                last_year_budget = Budget.objects.filter(
                    department=department,
                    category=category,
                    status='approved'
                ).order_by('-academic_year__start_date').first()
                
                if last_year_budget:
                    prediction_data['predicted_amount'] = float(last_year_budget.amount) * 1.05  # 5% increase
                    prediction_data['confidence_score'] = 0.3
                    prediction_data['factors']['prediction_details']['method'] = 'last_year_with_increase'
                    prediction_data['factors']['prediction_details']['last_year_amount'] = float(last_year_budget.amount)
                else:
                    # No historical data at all, use a default amount
                    prediction_data['predicted_amount'] = 50000  # Default amount
                    prediction_data['confidence_score'] = 0.1
                    prediction_data['factors']['prediction_details']['method'] = 'default_amount'
        
        # Adjust prediction based on expense trends if requested
        if include_expense_trends:
            from expenses.models import Expense
            
            # Get expense data for this department and category for the last year
            last_year_date = timezone.now().date() - datetime.timedelta(days=365)
            expenses = Expense.objects.filter(
                department=department,
                date__gte=last_year_date
            )
            
            if expenses.exists():
                total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
                
                # Calculate monthly average
                monthly_avg = float(total_expenses) / 12
                
                # Project annual expenses
                projected_annual = monthly_avg * 12
                
                # Adjust prediction if expenses are higher than current prediction
                if projected_annual > prediction_data['predicted_amount']:
                    adjustment_factor = min(1.2, projected_annual / prediction_data['predicted_amount'])
                    prediction_data['predicted_amount'] *= adjustment_factor
                    prediction_data['confidence_score'] = min(0.85, prediction_data['confidence_score'] + 0.1)
                    
                    # Store expense trend data
                    prediction_data['factors']['expense_trends']['last_year_expenses'] = float(total_expenses)
                    prediction_data['factors']['expense_trends']['monthly_average'] = float(monthly_avg)
                    prediction_data['factors']['expense_trends']['projected_annual'] = float(projected_annual)
                    prediction_data['factors']['expense_trends']['adjustment_factor'] = float(adjustment_factor)
        
        # Adjust for department growth if requested
        if include_department_growth:
            # For educational institutions, growth could be measured by student count, staff count, etc.
            # For this example, we'll use a simple growth factor based on department's budget history
            
            dept_budgets_by_year = {}
            for budget in Budget.objects.filter(department=department, status='approved'):
                year = budget.academic_year.start_date.year
                if year not in dept_budgets_by_year:
                    dept_budgets_by_year[year] = 0
                dept_budgets_by_year[year] += float(budget.amount)
            
            # Calculate growth rate if we have at least 2 years of data
            years = sorted(dept_budgets_by_year.keys())
            if len(years) >= 2:
                earliest_year = years[0]
                latest_year = years[-1]
                
                if latest_year > earliest_year:
                    growth_rate = (dept_budgets_by_year[latest_year] / dept_budgets_by_year[earliest_year]) ** (1 / (latest_year - earliest_year)) - 1
                    
                    # Apply growth rate to prediction (cap at 20% growth)
                    growth_factor = min(1.2, 1 + growth_rate)
                    prediction_data['predicted_amount'] *= growth_factor
                    
                    # Store growth data
                    prediction_data['factors']['department_growth']['earliest_year'] = earliest_year
                    prediction_data['factors']['department_growth']['latest_year'] = latest_year
                    prediction_data['factors']['department_growth']['growth_rate'] = float(growth_rate)
                    prediction_data['factors']['department_growth']['growth_factor'] = float(growth_factor)
        
        # Apply inflation adjustment (assuming 3% annual inflation)
        inflation_rate = 0.03
        prediction_data['predicted_amount'] *= (1 + inflation_rate)
        prediction_data['factors']['inflation_adjustment']['rate'] = inflation_rate
        
        # Round the predicted amount to a reasonable value
        prediction_data['predicted_amount'] = round(prediction_data['predicted_amount'], -2)  # Round to nearest 100
        
        # Ensure prediction is positive
        prediction_data['predicted_amount'] = max(1000, prediction_data['predicted_amount'])
        
        return prediction_data
        
    except Exception as e:
        logger.error(f"Error generating budget prediction: {str(e)}")
        
        # Return a fallback prediction
        return {
            'predicted_amount': 50000,  # Default fallback amount
            'confidence_score': 0.1,    # Low confidence
            'factors': {
                'error': str(e),
                'fallback': True
            }
        }
