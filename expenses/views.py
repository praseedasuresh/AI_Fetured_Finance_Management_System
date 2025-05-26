from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse
import csv
import datetime

from .models import ExpenseCategory, Expense, ExpenseAttachment, RecurringExpense
from .forms import (
    ExpenseCategoryForm, ExpenseForm, ExpenseAttachmentForm, ExpenseApprovalForm,
    ExpensePaymentForm, RecurringExpenseForm, ExpenseSearchForm
)
from users.decorators import admin_required, finance_staff_required
from core.models import AcademicYear, Department


@finance_staff_required
def expense_dashboard(request):
    """Dashboard view for expense management"""
    # Get current academic year
    current_year = AcademicYear.get_active()
    
    # Get expense statistics
    total_expenses = Expense.objects.filter(
        academic_year=current_year,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Get department-wise expense distribution
    department_expenses = Expense.objects.filter(
        academic_year=current_year,
        status='paid'
    ).values('department__name').annotate(total=Sum('amount')).order_by('-total')
    
    # Get category-wise expense distribution
    category_expenses = Expense.objects.filter(
        academic_year=current_year,
        status='paid'
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    # Get recent expenses
    recent_expenses = Expense.objects.filter(
        academic_year=current_year
    ).order_by('-date')[:10]
    
    # Get pending expense approvals
    pending_approvals = Expense.objects.filter(status='submitted').order_by('-date')[:10]
    
    # Get upcoming recurring expenses
    upcoming_recurring = RecurringExpense.objects.filter(
        is_active=True,
        next_due_date__lte=timezone.now().date() + datetime.timedelta(days=30)
    ).order_by('next_due_date')[:10]
    
    context = {
        'total_expenses': total_expenses,
        'department_expenses': department_expenses,
        'category_expenses': category_expenses,
        'recent_expenses': recent_expenses,
        'pending_approvals': pending_approvals,
        'upcoming_recurring': upcoming_recurring,
        'current_year': current_year,
    }
    
    return render(request, 'expenses/dashboard.html', context)


# Expense Category Views
@finance_staff_required
def expense_category_list(request):
    """View for listing expense categories"""
    categories = ExpenseCategory.objects.all()
    return render(request, 'expenses/category/list.html', {'categories': categories})


@finance_staff_required
def expense_category_create(request):
    """View for creating a new expense category"""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category created successfully!')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm()
    
    return render(request, 'expenses/category/form.html', {'form': form, 'title': 'Create Expense Category'})


@finance_staff_required
def expense_category_update(request, pk):
    """View for updating an expense category"""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category updated successfully!')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    
    return render(request, 'expenses/category/form.html', {'form': form, 'title': 'Update Expense Category'})


@finance_staff_required
def expense_category_delete(request, pk):
    """View for deleting an expense category"""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, 'Expense category deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting expense category: {str(e)}')
        return redirect('expense_category_list')
    
    return render(request, 'expenses/category/delete.html', {'category': category})


@finance_staff_required
def export_expense_categories_csv(request):
    """View for exporting expense categories to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expense_categories.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow(['ID', 'Name', 'Description', 'Color', 'Is Active', 'Created At', 'Updated At'])
    
    # Write data rows
    categories = ExpenseCategory.objects.all().order_by('name')
    for category in categories:
        writer.writerow([
            category.id,
            category.name,
            category.description,
            category.color,
            'Yes' if category.is_active else 'No',
            category.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            category.updated_at.strftime('%Y-%m-%d %H:%M:%S') if category.updated_at else '',
        ])
    
    return response


# Expense Views
@finance_staff_required
def expense_list(request):
    """View for listing expenses"""
    # Get all expenses without any filtering initially
    expenses = Expense.objects.all().select_related('department', 'academic_year', 'category')
    
    # Check if we have any expenses at all
    total_expenses = expenses.count()
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        expenses = expenses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply form filters if the form is valid
    form = ExpenseSearchForm(request.GET)
    if form.is_valid():
        title = form.cleaned_data.get('title')
        department = form.cleaned_data.get('department')
        category = form.cleaned_data.get('category')
        academic_year = form.cleaned_data.get('academic_year')
        status = form.cleaned_data.get('status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        
        if title:
            expenses = expenses.filter(title__icontains=title)
        
        if department:
            expenses = expenses.filter(department=department)
        
        if category:
            expenses = expenses.filter(category=category)
        
        if academic_year:
            expenses = expenses.filter(academic_year=academic_year)
        
        if status:
            expenses = expenses.filter(status=status)
        
        if start_date and end_date:
            expenses = expenses.filter(date__range=[start_date, end_date])
    
    # Order the results
    expenses = expenses.order_by('-date')
    
    # Paginate the results
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add debug message if no expenses are found
    if total_expenses == 0:
        messages.info(request, 'No expenses found in the database. Create your first expense by clicking the "Add Expense" button above.')
    
    return render(request, 'expenses/expense/list.html', {
        'page_obj': page_obj,
        'form': form,
        'total_expenses': total_expenses
    })


@finance_staff_required
def expense_create(request):
    """View for creating a new expense"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.submitted_by = request.user
            expense.save()
            
            messages.success(request, 'Expense created successfully!')
            return redirect('expense_detail', pk=expense.pk)
    else:
        # Pre-fill academic year with active year
        initial = {'academic_year': AcademicYear.get_active()}
        form = ExpenseForm(initial=initial, user=request.user)
    
    return render(request, 'expenses/expense/form.html', {'form': form, 'title': 'Create Expense'})


@finance_staff_required
def expense_update(request, pk):
    """View for updating an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    # Only allow updates if expense is in draft or rejected status
    if expense.status not in ['draft', 'rejected']:
        messages.error(request, 'You can only edit expenses in draft or rejected status.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    
    return render(request, 'expenses/expense/form.html', {'form': form, 'title': 'Update Expense'})


@finance_staff_required
def expense_delete(request, pk):
    """View for deleting an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    # Only allow deletion if expense is in draft or rejected status
    if expense.status not in ['draft', 'rejected']:
        messages.error(request, 'You can only delete expenses in draft or rejected status.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        try:
            expense.delete()
            messages.success(request, 'Expense deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting expense: {str(e)}')
        return redirect('expense_list')
    
    return render(request, 'expenses/expense/delete.html', {'expense': expense})


@finance_staff_required
def expense_detail(request, pk):
    """View for viewing expense details"""
    expense = get_object_or_404(Expense, pk=pk)
    attachments = ExpenseAttachment.objects.filter(expense=expense)
    
    context = {
        'expense': expense,
        'attachments': attachments,
    }
    
    return render(request, 'expenses/expense/detail.html', context)


@finance_staff_required
def expense_add_attachment(request, pk):
    """View for adding attachments to an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.expense = expense
            attachment.save()
            
            messages.success(request, 'Attachment added successfully!')
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseAttachmentForm()
    
    return render(request, 'expenses/expense/attachment_form.html', {
        'form': form,
        'expense': expense,
        'title': 'Add Attachment'
    })


@finance_staff_required
def expense_delete_attachment(request, expense_pk, attachment_pk):
    """View for deleting an attachment"""
    attachment = get_object_or_404(ExpenseAttachment, pk=attachment_pk, expense_id=expense_pk)
    
    if request.method == 'POST':
        try:
            attachment.delete()
            messages.success(request, 'Attachment deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting attachment: {str(e)}')
        return redirect('expense_detail', pk=expense_pk)
    
    return render(request, 'expenses/expense/attachment_delete.html', {'attachment': attachment})


@admin_required
def expense_approval(request, pk):
    """View for approving or rejecting expenses"""
    expense = get_object_or_404(Expense, pk=pk)
    
    # Only allow approval if expense is in submitted status
    if expense.status != 'submitted':
        messages.error(request, 'You can only approve expenses in submitted status.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        form = ExpenseApprovalForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data.get('decision')
            rejection_reason = form.cleaned_data.get('rejection_reason')
            
            if decision == 'approve':
                expense.approve(request.user)
                messages.success(request, 'Expense approved successfully!')
            else:
                expense.reject(rejection_reason)
                messages.success(request, 'Expense rejected successfully!')
            
            return redirect('expense_list')
    else:
        form = ExpenseApprovalForm()
    
    return render(request, 'expenses/expense/approval.html', {'form': form, 'expense': expense})


@finance_staff_required
def expense_payment(request, pk):
    """View for marking expenses as paid"""
    expense = get_object_or_404(Expense, pk=pk)
    
    # Only allow payment if expense is in approved status
    if expense.status != 'approved':
        messages.error(request, 'You can only mark approved expenses as paid.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        form = ExpensePaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data.get('payment_method')
            payment_reference = form.cleaned_data.get('payment_reference')
            payment_date = form.cleaned_data.get('payment_date')
            
            expense.mark_as_paid(payment_method, payment_reference, payment_date)
            messages.success(request, 'Expense marked as paid successfully!')
            
            return redirect('expense_list')
    else:
        form = ExpensePaymentForm(initial={'payment_date': timezone.now().date()})
    
    return render(request, 'expenses/expense/payment.html', {'form': form, 'expense': expense})


@finance_staff_required
def export_expenses_csv(request):
    """View for exporting expenses to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    
    # Get filter parameters from request
    title = request.GET.get('title')
    department_id = request.GET.get('department')
    category_id = request.GET.get('category')
    academic_year_id = request.GET.get('academic_year')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    expenses = Expense.objects.all()
    
    if title:
        expenses = expenses.filter(title__icontains=title)
    
    if department_id:
        expenses = expenses.filter(department_id=department_id)
    
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    
    if academic_year_id:
        expenses = expenses.filter(academic_year_id=academic_year_id)
    
    if status:
        expenses = expenses.filter(status=status)
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            expenses = expenses.filter(date__range=[start_date, end_date])
        except ValueError:
            pass
    
    writer = csv.writer(response)
    writer.writerow([
        'Title', 'Description', 'Amount', 'Date', 'Category', 'Department',
        'Academic Year', 'Status', 'Submitted By', 'Approved By', 'Approved Date',
        'Payment Method', 'Payment Date', 'Payment Reference'
    ])
    
    for expense in expenses:
        writer.writerow([
            expense.title,
            expense.description,
            expense.amount,
            expense.date.strftime('%Y-%m-%d'),
            expense.category.name,
            expense.department.name,
            expense.academic_year.name,
            expense.get_status_display(),
            expense.submitted_by.get_full_name(),
            expense.approved_by.get_full_name() if expense.approved_by else '',
            expense.approved_date.strftime('%Y-%m-%d %H:%M') if expense.approved_date else '',
            expense.get_payment_method_display() if expense.payment_method else '',
            expense.payment_date.strftime('%Y-%m-%d') if expense.payment_date else '',
            expense.payment_reference or ''
        ])
    
    return response


# Recurring Expense Views
@finance_staff_required
def recurring_expense_list(request):
    """View for listing recurring expenses"""
    recurring_expenses = RecurringExpense.objects.all().order_by('next_due_date')
    
    # Filter by active status if provided
    is_active = request.GET.get('is_active')
    if is_active == 'true':
        recurring_expenses = recurring_expenses.filter(is_active=True)
    elif is_active == 'false':
        recurring_expenses = recurring_expenses.filter(is_active=False)
    
    paginator = Paginator(recurring_expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'expenses/recurring/list.html', {'page_obj': page_obj})


@finance_staff_required
def recurring_expense_create(request):
    """View for creating a new recurring expense"""
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            recurring_expense = form.save(commit=False)
            recurring_expense.created_by = request.user
            recurring_expense.save()
            
            messages.success(request, 'Recurring expense created successfully!')
            return redirect('recurring_expense_list')
    else:
        form = RecurringExpenseForm(user=request.user)
    
    return render(request, 'expenses/recurring/form.html', {'form': form, 'title': 'Create Recurring Expense'})


@finance_staff_required
def recurring_expense_update(request, pk):
    """View for updating a recurring expense"""
    recurring_expense = get_object_or_404(RecurringExpense, pk=pk)
    
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, instance=recurring_expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurring expense updated successfully!')
            return redirect('recurring_expense_list')
    else:
        form = RecurringExpenseForm(instance=recurring_expense, user=request.user)
    
    return render(request, 'expenses/recurring/form.html', {'form': form, 'title': 'Update Recurring Expense'})


@finance_staff_required
def recurring_expense_delete(request, pk):
    """View for deleting a recurring expense"""
    recurring_expense = get_object_or_404(RecurringExpense, pk=pk)
    
    if request.method == 'POST':
        try:
            recurring_expense.delete()
            messages.success(request, 'Recurring expense deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting recurring expense: {str(e)}')
        return redirect('recurring_expense_list')
    
    return render(request, 'expenses/recurring/delete.html', {'recurring_expense': recurring_expense})


@finance_staff_required
def recurring_expense_toggle_active(request, pk):
    """View for toggling the active status of a recurring expense"""
    recurring_expense = get_object_or_404(RecurringExpense, pk=pk)
    
    recurring_expense.is_active = not recurring_expense.is_active
    recurring_expense.save()
    
    status = 'activated' if recurring_expense.is_active else 'deactivated'
    messages.success(request, f'Recurring expense {status} successfully!')
    
    return redirect('recurring_expense_list')


@finance_staff_required
def recurring_expense_create_now(request, pk):
    """View for creating an expense from a recurring expense immediately"""
    recurring_expense = get_object_or_404(RecurringExpense, pk=pk)
    
    if not recurring_expense.is_active:
        messages.error(request, 'Cannot create expense from inactive recurring expense.')
        return redirect('recurring_expense_list')
    
    expense = recurring_expense.create_expense()
    
    if expense:
        messages.success(request, 'Expense created successfully from recurring expense!')
        return redirect('expense_detail', pk=expense.pk)
    else:
        messages.error(request, 'Failed to create expense from recurring expense.')
        return redirect('recurring_expense_list')


@finance_staff_required
def export_recurring_expense_csv(request):
    """View for exporting recurring expenses to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="recurring_expenses.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'ID', 'Title', 'Category', 'Department', 'Amount', 'Frequency', 
        'Next Due Date', 'Description', 'Payment Method', 'Is Active', 
        'Created At', 'Created By'
    ])
    
    # Write data rows
    recurring_expenses = RecurringExpense.objects.all().order_by('-next_due_date')
    for expense in recurring_expenses:
        writer.writerow([
            expense.id,
            expense.title,
            expense.category.name if expense.category else '',
            expense.department.name if expense.department else '',
            expense.amount,
            expense.get_frequency_display(),
            expense.next_due_date.strftime('%Y-%m-%d') if expense.next_due_date else '',
            expense.description,
            expense.get_payment_method_display() if expense.payment_method else '',
            'Yes' if expense.is_active else 'No',
            expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            expense.created_by.get_full_name() if expense.created_by else '',
        ])
    
    return response
