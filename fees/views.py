from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
import csv
import datetime

from .models import FeeCategory, FeeStructure, StudentFee, FeePayment, FeeDiscount
from .forms import (
    FeeCategoryForm, FeeStructureForm, StudentFeeForm, FeePaymentForm,
    FeeDiscountForm, BulkFeeAssignmentForm, FeeSearchForm
)
from users.models import User
from core.models import AcademicYear, Department
from users.decorators import admin_required, finance_staff_required


@finance_staff_required
def fee_dashboard(request):
    """Dashboard view for fee management"""
    # Get current academic year
    current_year = AcademicYear.get_active()
    
    # Get fee collection statistics
    total_fees = StudentFee.objects.filter(
        fee_structure__academic_year=current_year
    ).aggregate(
        total=Sum('amount'),
        waived=Sum('waiver_amount')
    )
    
    total_collected = FeePayment.objects.filter(
        academic_year=current_year,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_pending = (total_fees.get('total') or 0) - (total_fees.get('waived') or 0) - total_collected
    
    # Get recent payments
    recent_payments = FeePayment.objects.filter(status='paid').order_by('-payment_date')[:10]
    
    # Get overdue fees
    overdue_fees = StudentFee.objects.filter(
        is_paid=False,
        due_date__lt=timezone.now().date()
    ).order_by('due_date')[:10]
    
    context = {
        'total_fees': total_fees.get('total') or 0,
        'total_waived': total_fees.get('waived') or 0,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'collection_percentage': (total_collected / (total_fees.get('total') or 1)) * 100,
        'recent_payments': recent_payments,
        'overdue_fees': overdue_fees,
        'current_year': current_year,
    }
    
    return render(request, 'fees/dashboard.html', context)


# Fee Category Views
@finance_staff_required
def fee_category_list(request):
    """View for listing fee categories"""
    categories = FeeCategory.objects.all()
    return render(request, 'fees/category/list.html', {'categories': categories})


@finance_staff_required
def fee_category_create(request):
    """View for creating a new fee category"""
    if request.method == 'POST':
        form = FeeCategoryForm(request.POST)
        if form.is_valid():
            try:
                # Save the form data to create a new fee category
                category = form.save()
                messages.success(request, f'Fee category "{category.name}" created successfully!')
                return redirect('fee_category_list')
            except Exception as e:
                # Log the error and show it to the user
                messages.error(request, f'Error creating fee category: {str(e)}')
                print(f"Error creating fee category: {str(e)}")
        else:
            # Form is not valid, show field errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FeeCategoryForm()
    
    return render(request, 'fees/category/form.html', {'form': form, 'title': 'Create Fee Category'})


@finance_staff_required
def fee_category_update(request, pk):
    """View for updating a fee category"""
    category = get_object_or_404(FeeCategory, pk=pk)
    
    if request.method == 'POST':
        form = FeeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee category updated successfully!')
            return redirect('fee_category_list')
    else:
        form = FeeCategoryForm(instance=category)
    
    return render(request, 'fees/category/form.html', {'form': form, 'title': 'Update Fee Category'})


@finance_staff_required
def fee_category_delete(request, pk):
    """View for deleting a fee category"""
    category = get_object_or_404(FeeCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, 'Fee category deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting fee category: {str(e)}')
        return redirect('fee_category_list')
    
    return render(request, 'fees/category/delete.html', {'category': category})


# Fee Structure Views
@finance_staff_required
def fee_structure_list(request):
    """View for listing fee structures"""
    structures = FeeStructure.objects.all()
    return render(request, 'fees/structure/list.html', {'structures': structures})


@finance_staff_required
def fee_structure_create(request):
    """View for creating a new fee structure"""
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            try:
                # Save the form data to create a new fee structure
                structure = form.save()
                messages.success(request, f'Fee structure "{structure.name}" created successfully!')
                return redirect('fee_structure_list')
            except Exception as e:
                # Log the error and show it to the user
                messages.error(request, f'Error creating fee structure: {str(e)}')
                print(f"Error creating fee structure: {str(e)}")
        else:
            # Form is not valid, show field errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FeeStructureForm()
    
    return render(request, 'fees/structure/form.html', {'form': form, 'title': 'Create Fee Structure'})


@finance_staff_required
def fee_structure_update(request, pk):
    """View for updating a fee structure"""
    structure = get_object_or_404(FeeStructure, pk=pk)
    
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee structure updated successfully!')
            return redirect('fee_structure_list')
    else:
        form = FeeStructureForm(instance=structure)
    
    return render(request, 'fees/structure/form.html', {'form': form, 'title': 'Update Fee Structure'})


@finance_staff_required
def fee_structure_delete(request, pk):
    """View for deleting a fee structure"""
    structure = get_object_or_404(FeeStructure, pk=pk)
    
    if request.method == 'POST':
        try:
            structure.delete()
            messages.success(request, 'Fee structure deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting fee structure: {str(e)}')
        return redirect('fee_structure_list')
    
    return render(request, 'fees/structure/delete.html', {'structure': structure})


# Student Fee Views
@finance_staff_required
def student_fee_list(request):
    """View for listing student fees"""
    form = FeeSearchForm(request.GET)
    student_fees = StudentFee.objects.all()
    
    if form.is_valid():
        student_query = form.cleaned_data.get('student')
        department = form.cleaned_data.get('department')
        academic_year = form.cleaned_data.get('academic_year')
        is_paid = form.cleaned_data.get('is_paid')
        
        if student_query:
            student_fees = student_fees.filter(
                Q(student__first_name__icontains=student_query) | 
                Q(student__last_name__icontains=student_query) |
                Q(student__email__icontains=student_query) |
                Q(student__student_id__icontains=student_query)
            )
        
        if department:
            student_fees = student_fees.filter(student__department=department)
        
        if academic_year:
            student_fees = student_fees.filter(fee_structure__academic_year=academic_year)
        
        if is_paid == 'paid':
            student_fees = student_fees.filter(is_paid=True)
        elif is_paid == 'unpaid':
            student_fees = student_fees.filter(is_paid=False)
    
    paginator = Paginator(student_fees.order_by('-due_date'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'fees/student_fee/list.html', {
        'page_obj': page_obj,
        'form': form
    })


@finance_staff_required
def student_fee_create(request):
    """View for creating a new student fee"""
    if request.method == 'POST':
        form = StudentFeeForm(request.POST)
        if form.is_valid():
            try:
                # Save the form data to create a new student fee
                student_fee = form.save()
                messages.success(request, f'Fee for {student_fee.student.get_full_name()} created successfully!')
                return redirect('student_fee_list')
            except Exception as e:
                # Log the error and show it to the user
                messages.error(request, f'Error creating student fee: {str(e)}')
                print(f"Error creating student fee: {str(e)}")
        else:
            # Form is not valid, show field errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentFeeForm()
    
    return render(request, 'fees/student_fee/form.html', {'form': form, 'title': 'Assign Fee to Student'})


@finance_staff_required
def student_fee_update(request, pk):
    """View for updating a student fee"""
    student_fee = get_object_or_404(StudentFee, pk=pk)
    
    if request.method == 'POST':
        form = StudentFeeForm(request.POST, instance=student_fee)
        if form.is_valid():
            student_fee = form.save()
            messages.success(request, f'Fee for {student_fee.student.get_full_name()} updated successfully!')
            return redirect('student_fee_list')
    else:
        form = StudentFeeForm(instance=student_fee)
    
    return render(request, 'fees/student_fee/form.html', {'form': form, 'title': 'Update Student Fee'})


@finance_staff_required
def student_fee_delete(request, pk):
    """View for deleting a student fee"""
    student_fee = get_object_or_404(StudentFee, pk=pk)
    
    if request.method == 'POST':
        student_name = student_fee.student.get_full_name()
        try:
            student_fee.delete()
            messages.success(request, f'Fee for {student_name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting fee: {str(e)}')
        return redirect('student_fee_list')
    
    return render(request, 'fees/student_fee/delete.html', {'student_fee': student_fee})


@finance_staff_required
def bulk_fee_assignment(request):
    """View for assigning fees to multiple students at once"""
    if request.method == 'POST':
        form = BulkFeeAssignmentForm(request.POST)
        if form.is_valid():
            department = form.cleaned_data.get('department')
            fee_structure = form.cleaned_data.get('fee_structure')
            due_date = form.cleaned_data.get('due_date')
            
            # Get students based on department or all students if no department is specified
            if department:
                students = User.objects.filter(role='student', department=department)
            else:
                students = User.objects.filter(role='student')
            
            # Create student fees
            count = 0
            for student in students:
                # Check if fee already exists
                if not StudentFee.objects.filter(student=student, fee_structure=fee_structure).exists():
                    StudentFee.objects.create(
                        student=student,
                        fee_structure=fee_structure,
                        amount=fee_structure.amount,
                        due_date=due_date
                    )
                    count += 1
            
            messages.success(request, f'Fee assigned to {count} students successfully!')
            return redirect('student_fee_list')
    else:
        form = BulkFeeAssignmentForm()
    
    return render(request, 'fees/student_fee/bulk_assignment.html', {'form': form})


# Fee Payment Views
@finance_staff_required
def fee_payment_list(request):
    """View for listing fee payments"""
    payments = FeePayment.objects.all().order_by('-payment_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'fees/payment/list.html', {'page_obj': page_obj})


@finance_staff_required
def fee_payment_create(request):
    """View for creating a new fee payment"""
    if request.method == 'POST':
        form = FeePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.collected_by = request.user
            payment.save()
            
            messages.success(request, f'Payment for {payment.student.get_full_name()} recorded successfully!')
            return redirect('fee_payment_list')
    else:
        # Pre-fill academic year with active year
        initial = {'academic_year': AcademicYear.get_active()}
        form = FeePaymentForm(initial=initial)
    
    return render(request, 'fees/payment/form.html', {'form': form, 'title': 'Record Fee Payment'})


@finance_staff_required
def fee_payment_update(request, pk):
    """View for updating a fee payment"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    if request.method == 'POST':
        form = FeePaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Payment for {payment.student.get_full_name()} updated successfully!')
            return redirect('fee_payment_list')
    else:
        form = FeePaymentForm(instance=payment)
    
    return render(request, 'fees/payment/form.html', {'form': form, 'title': 'Update Fee Payment'})


@finance_staff_required
def fee_payment_delete(request, pk):
    """View for deleting a fee payment"""
    payment = get_object_or_404(FeePayment, pk=pk)
    
    if request.method == 'POST':
        student_name = payment.student.get_full_name()
        
        # If this payment was linked to a student fee and was marked as paid,
        # we need to revert the student fee to unpaid
        if payment.status == 'paid' and payment.student_fee:
            payment.student_fee.is_paid = False
            payment.student_fee.save()
        
        try:
            payment.delete()
            messages.success(request, f'Payment for {student_name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting payment: {str(e)}')
        return redirect('fee_payment_list')
    
    return render(request, 'fees/payment/delete.html', {'payment': payment})


@finance_staff_required
def export_payments_csv(request):
    """View for exporting payments to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fee_payments.csv"'
    
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    payments = FeePayment.objects.all().order_by('-payment_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    writer = csv.writer(response)
    writer.writerow([
        'Receipt Number', 'Student ID', 'Student Name', 'Amount', 'Payment Date',
        'Payment Method', 'Status', 'Transaction ID', 'Academic Year', 'Collected By'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.receipt_number,
            payment.student.student_id,
            payment.student.get_full_name(),
            payment.amount,
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.get_payment_method_display(),
            payment.get_status_display(),
            payment.transaction_id or '',
            payment.academic_year.name,
            payment.collected_by.get_full_name() if payment.collected_by else ''
        ])
    
    return response


# API Endpoints
@finance_staff_required
def student_fees_api(request, student_id):
    """API endpoint to fetch student fees for a specific student"""
    from django.http import JsonResponse
    
    # Get unpaid student fees for the specified student
    student_fees = StudentFee.objects.filter(student_id=student_id, is_paid=False)
    
    # Prepare the data for JSON response
    fees_data = []
    for fee in student_fees:
        fees_data.append({
            'id': fee.id,
            'fee_structure_name': fee.fee_structure.name,
            'amount': float(fee.amount),
            'due_date': fee.due_date.strftime('%Y-%m-%d'),
            'is_overdue': fee.due_date < timezone.now().date()
        })
    
    return JsonResponse(fees_data, safe=False)


# Student Fee Views (for students)
@login_required
def student_fee_history(request):
    """View for students to see their fee history"""
    if not request.user.is_student:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    student_fees = StudentFee.objects.filter(student=request.user).order_by('-due_date')
    payments = FeePayment.objects.filter(student=request.user).order_by('-payment_date')
    
    # Calculate total fees and payments
    total_fees = student_fees.aggregate(
        total=Sum('amount'),
        waived=Sum('waiver_amount')
    )
    
    total_paid = payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    total_pending = (total_fees.get('total') or 0) - (total_fees.get('waived') or 0) - total_paid
    
    context = {
        'student_fees': student_fees,
        'payments': payments,
        'total_fees': total_fees.get('total') or 0,
        'total_waived': total_fees.get('waived') or 0,
        'total_paid': total_paid,
        'total_pending': total_pending,
    }
    
    return render(request, 'fees/student/fee_history.html', context)
