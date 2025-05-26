from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
import json
import csv
import datetime
import io
import xlsxwriter
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .models import ReportTemplate, SavedReport, ScheduledReport
from .forms import (
    ReportTemplateForm, SavedReportForm, ScheduledReportForm, ReportGenerationForm
)
from users.decorators import admin_required, finance_staff_required
from core.models import AcademicYear, Department
from fees.models import FeePayment, StudentFee
from budget.models import Budget, BudgetAllocation, BudgetTransfer
from expenses.models import Expense


@finance_staff_required
def report_dashboard(request):
    """Dashboard view for reports"""
    # Get current academic year
    current_year = AcademicYear.get_active()
    
    # Get report statistics
    total_templates = ReportTemplate.objects.count()
    total_saved_reports = SavedReport.objects.filter(academic_year=current_year).count()
    total_scheduled_reports = ScheduledReport.objects.filter(is_active=True).count()
    
    # Get recent reports
    recent_reports = SavedReport.objects.filter(
        academic_year=current_year
    ).order_by('-created_at')[:10]
    
    # Get upcoming scheduled reports
    upcoming_scheduled = ScheduledReport.objects.filter(
        is_active=True,
        next_run__gte=timezone.now()
    ).order_by('next_run')[:10]
    
    context = {
        'total_templates': total_templates,
        'total_saved_reports': total_saved_reports,
        'total_scheduled_reports': total_scheduled_reports,
        'recent_reports': recent_reports,
        'upcoming_scheduled': upcoming_scheduled,
        'current_year': current_year,
    }
    
    return render(request, 'reports/dashboard.html', context)


# Report Template Views
@finance_staff_required
def template_list(request):
    """View for listing report templates"""
    # Filter templates based on user access
    if request.user.is_superuser or request.user.role == 'admin':
        templates = ReportTemplate.objects.all()
    else:
        templates = ReportTemplate.objects.filter(
            Q(is_system=True) | Q(created_by=request.user)
        )
    
    return render(request, 'reports/template/list.html', {'templates': templates})


@finance_staff_required
def template_create(request):
    """View for creating a new report template"""
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            
            messages.success(request, 'Report template created successfully!')
            return redirect('template_list')
    else:
        form = ReportTemplateForm()
    
    return render(request, 'reports/template/form.html', {'form': form, 'title': 'Create Report Template'})


@finance_staff_required
def template_update(request, pk):
    """View for updating a report template"""
    template = get_object_or_404(ReportTemplate, pk=pk)
    
    # Check if user has permission to edit this template
    if not (request.user.is_superuser or request.user.role == 'admin' or template.created_by == request.user):
        messages.error(request, 'You do not have permission to edit this template.')
        return redirect('template_list')
    
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Report template updated successfully!')
            return redirect('template_list')
    else:
        form = ReportTemplateForm(instance=template)
    
    return render(request, 'reports/template/form.html', {'form': form, 'title': 'Update Report Template'})


@finance_staff_required
def template_delete(request, pk):
    """View for deleting a report template"""
    template = get_object_or_404(ReportTemplate, pk=pk)
    
    # Check if user has permission to delete this template
    if not (request.user.is_superuser or request.user.role == 'admin' or template.created_by == request.user):
        messages.error(request, 'You do not have permission to delete this template.')
        return redirect('template_list')
    
    # System templates cannot be deleted
    if template.is_system:
        messages.error(request, 'System templates cannot be deleted.')
        return redirect('template_list')
    
    if request.method == 'POST':
        try:
            template.delete()
            messages.success(request, 'Report template deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting report template: {str(e)}')
        return redirect('template_list')
    
    return render(request, 'reports/template/delete.html', {'template': template})


@finance_staff_required
def template_detail(request, pk):
    """View for viewing template details"""
    template = get_object_or_404(ReportTemplate, pk=pk)
    
    # Check if user has permission to view this template
    if not (request.user.is_superuser or request.user.role == 'admin' or 
            template.is_system or template.created_by == request.user):
        messages.error(request, 'You do not have permission to view this template.')
        return redirect('template_list')
    
    context = {
        'template': template,
    }
    
    return render(request, 'reports/template/detail.html', context)


# Saved Report Views
@finance_staff_required
def saved_report_list(request):
    """View for listing saved reports"""
    # Filter reports based on user access
    if request.user.is_superuser or request.user.role == 'admin':
        reports = SavedReport.objects.all()
    else:
        reports = SavedReport.objects.filter(
            Q(created_by=request.user) | 
            Q(department=request.user.department)
        )
    
    paginator = Paginator(reports.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'reports/saved/list.html', {'page_obj': page_obj})


@finance_staff_required
def saved_report_detail(request, pk):
    """View for viewing saved report details"""
    report = get_object_or_404(SavedReport, pk=pk)
    
    # Check if user has permission to view this report
    if not (request.user.is_superuser or request.user.role == 'admin' or 
            report.created_by == request.user or report.department == request.user.department):
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('saved_report_list')
    
    context = {
        'report': report,
    }
    
    return render(request, 'reports/saved/detail.html', context)


@finance_staff_required
def saved_report_delete(request, pk):
    """View for deleting a saved report"""
    report = get_object_or_404(SavedReport, pk=pk)
    
    # Check if user has permission to delete this report
    if not (request.user.is_superuser or request.user.role == 'admin' or report.created_by == request.user):
        messages.error(request, 'You do not have permission to delete this report.')
        return redirect('saved_report_list')
    
    if request.method == 'POST':
        try:
            report.delete()
            messages.success(request, 'Report deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting report: {str(e)}')
        return redirect('saved_report_list')
    
    return render(request, 'reports/saved/delete.html', {'report': report})


@finance_staff_required
def saved_report_download(request, pk):
    """View for downloading a saved report"""
    report = get_object_or_404(SavedReport, pk=pk)
    
    # Check if user has permission to download this report
    if not (request.user.is_superuser or request.user.role == 'admin' or 
            report.created_by == request.user or report.department == request.user.department):
        messages.error(request, 'You do not have permission to download this report.')
        return redirect('saved_report_list')
    
    # If report has a file, serve it
    if report.file:
        response = HttpResponse(report.file, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
        return response
    
    # Otherwise, generate the file based on report data
    format_type = request.GET.get('format', 'pdf')
    
    if format_type == 'csv':
        return _generate_csv_report(report)
    elif format_type == 'excel':
        return _generate_excel_report(report)
    else:
        return _generate_pdf_report(report)


# Report Generation Views
@finance_staff_required
def generate_report(request):
    """View for generating a new report"""
    if request.method == 'POST':
        form = ReportGenerationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                template = form.cleaned_data.get('template')
                academic_year = form.cleaned_data.get('academic_year')
                department = form.cleaned_data.get('department')
                start_date = form.cleaned_data.get('start_date')
                end_date = form.cleaned_data.get('end_date')
                include_details = form.cleaned_data.get('include_details')
                format_type = form.cleaned_data.get('format')
                
                # Generate report data based on template type
                report_data = _generate_report_data(
                    template.report_type,
                    academic_year,
                    department,
                    start_date,
                    end_date,
                    include_details
                )
                
                # Save the report
                report = SavedReport(
                    title=f"{template.title} - {academic_year.name}",
                    description=f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    template=template,
                    report_data=report_data,
                    parameters={
                        'academic_year': academic_year.id,
                        'department': department.id if department else None,
                        'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
                        'end_date': end_date.strftime('%Y-%m-%d') if end_date else None,
                        'include_details': include_details,
                        'format': format_type
                    },
                    academic_year=academic_year,
                    department=department,
                    created_by=request.user
                )
                report.save()
                
                messages.success(request, 'Report generated successfully!')
                
                # Redirect to download the report
                return redirect('saved_report_download', pk=report.pk)
            except Exception as e:
                messages.error(request, f'Error generating report: {str(e)}')
    else:
        form = ReportGenerationForm(user=request.user)
    
    return render(request, 'reports/generate.html', {'form': form})


# Scheduled Report Views
@finance_staff_required
def scheduled_report_list(request):
    """View for listing scheduled reports"""
    # Filter reports based on user access
    if request.user.is_superuser or request.user.role == 'admin':
        reports = ScheduledReport.objects.all()
    else:
        reports = ScheduledReport.objects.filter(created_by=request.user)
    
    return render(request, 'reports/scheduled/list.html', {'reports': reports})


@finance_staff_required
def scheduled_report_create(request):
    """View for creating a new scheduled report"""
    if request.method == 'POST':
        form = ScheduledReportForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                report = form.save(commit=False)
                report.created_by = request.user
                
                # Set default parameters (empty JSON object)
                report.parameters = {}
                
                # Calculate initial next_run date if not provided
                if not report.next_run:
                    report.calculate_next_run()
                    
                report.save()
                
                # Save many-to-many relationships
                form.save_m2m()
                
                messages.success(request, 'Scheduled report created successfully!')
                return redirect('scheduled_report_list')
            except Exception as e:
                messages.error(request, f'Error creating scheduled report: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ScheduledReportForm(user=request.user)
    
    return render(request, 'reports/scheduled/form.html', {'form': form, 'title': 'Create Scheduled Report'})


@finance_staff_required
def scheduled_report_update(request, pk):
    """View for updating a scheduled report"""
    report = get_object_or_404(ScheduledReport, pk=pk)
    
    # Check if user has permission to edit this report
    if not (request.user.is_superuser or request.user.role == 'admin' or report.created_by == request.user):
        messages.error(request, 'You do not have permission to edit this scheduled report.')
        return redirect('scheduled_report_list')
    
    if request.method == 'POST':
        form = ScheduledReportForm(request.POST, instance=report, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheduled report updated successfully!')
            return redirect('scheduled_report_list')
    else:
        form = ScheduledReportForm(instance=report, user=request.user)
    
    return render(request, 'reports/scheduled/form.html', {'form': form, 'title': 'Update Scheduled Report'})


@finance_staff_required
def scheduled_report_delete(request, pk):
    """View for deleting a scheduled report"""
    report = get_object_or_404(ScheduledReport, pk=pk)
    
    # Check if user has permission to delete this report
    if not (request.user.is_superuser or request.user.role == 'admin' or report.created_by == request.user):
        messages.error(request, 'You do not have permission to delete this scheduled report.')
        return redirect('scheduled_report_list')
    
    if request.method == 'POST':
        try:
            report.delete()
            messages.success(request, 'Scheduled report deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting scheduled report: {str(e)}')
        return redirect('scheduled_report_list')
    
    return render(request, 'reports/scheduled/delete.html', {'report': report})


@finance_staff_required
def scheduled_report_toggle_active(request, pk):
    """View for toggling the active status of a scheduled report"""
    report = get_object_or_404(ScheduledReport, pk=pk)
    
    # Check if user has permission to modify this report
    if not (request.user.is_superuser or request.user.role == 'admin' or report.created_by == request.user):
        messages.error(request, 'You do not have permission to modify this scheduled report.')
        return redirect('scheduled_report_list')
    
    # Toggle active status
    report.is_active = not report.is_active
    report.save()
    
    status = 'activated' if report.is_active else 'deactivated'
    messages.success(request, f'Scheduled report {status} successfully!')
    
    return redirect('scheduled_report_list')


@finance_staff_required
def scheduled_report_run_now(request, pk):
    """View for running a scheduled report immediately"""
    report = get_object_or_404(ScheduledReport, pk=pk)
    
    # Check if user has permission to run this report
    if not (request.user.is_superuser or request.user.role == 'admin' or report.created_by == request.user):
        messages.error(request, 'You do not have permission to run this scheduled report.')
        return redirect('scheduled_report_list')
    
    try:
        # Generate report data based on template type
        academic_year = AcademicYear.objects.get(id=report.parameters.get('academic_year'))
        
        department = None
        if report.parameters.get('department'):
            department = Department.objects.get(id=report.parameters.get('department'))
        
        # Parse dates if present
        start_date = None
        end_date = None
        if report.parameters.get('start_date'):
            start_date = datetime.datetime.strptime(report.parameters.get('start_date'), '%Y-%m-%d').date()
        if report.parameters.get('end_date'):
            end_date = datetime.datetime.strptime(report.parameters.get('end_date'), '%Y-%m-%d').date()
        
        # Generate report data
        report_data = _generate_report_data(
            report.template.report_type,
            academic_year,
            department,
            start_date,
            end_date,
            report.parameters.get('include_details', True)
        )
        
        # Save the report
        saved_report = SavedReport(
            title=f"{report.title} (Manual Run)",
            description=f"Manually generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            template=report.template,
            report_data=report_data,
            parameters=report.parameters,
            academic_year=academic_year,
            department=department,
            created_by=request.user
        )
        saved_report.save()
        
        messages.success(request, 'Report generated successfully!')
        return redirect('saved_report_detail', pk=saved_report.pk)
        
    except Exception as e:
        messages.error(request, f'Error running report: {str(e)}')
        return redirect('scheduled_report_list')


# Helper functions for report generation
def _generate_report_data(report_type, academic_year, department, start_date, end_date, include_details):
    """Generate report data based on report type and parameters"""
    if report_type == 'fee':
        return _generate_fee_report_data(academic_year, department, start_date, end_date, include_details)
    elif report_type == 'budget':
        return _generate_budget_report_data(academic_year, department, start_date, end_date, include_details)
    elif report_type == 'expense':
        return _generate_expense_report_data(academic_year, department, start_date, end_date, include_details)
    elif report_type == 'financial':
        return _generate_financial_summary_data(academic_year, department, start_date, end_date, include_details)
    else:
        return {}


def _generate_fee_report_data(academic_year, department, start_date, end_date, include_details):
    """Generate fee report data"""
    # Base query
    payments_query = FeePayment.objects.filter(student_fee__academic_year=academic_year)
    fees_query = StudentFee.objects.filter(academic_year=academic_year)
    
    # Apply filters
    if department:
        payments_query = payments_query.filter(student_fee__student__department=department)
        fees_query = fees_query.filter(student__department=department)
    
    if start_date and end_date:
        payments_query = payments_query.filter(payment_date__range=[start_date, end_date])
    
    # Calculate summary data
    total_fees = fees_query.aggregate(total=Sum('amount'))['total'] or 0
    total_paid = payments_query.aggregate(total=Sum('amount'))['total'] or 0
    total_due = total_fees - total_paid
    
    # Get detailed data if requested
    details = []
    if include_details:
        for fee in fees_query:
            paid_amount = FeePayment.objects.filter(student_fee=fee).aggregate(total=Sum('amount'))['total'] or 0
            details.append({
                'student': fee.student.user.get_full_name(),
                'fee_category': fee.fee_structure.category.name,
                'total_amount': float(fee.amount),
                'paid_amount': float(paid_amount),
                'due_amount': float(fee.amount) - float(paid_amount),
                'status': 'Paid' if paid_amount >= fee.amount else 'Partial' if paid_amount > 0 else 'Unpaid'
            })
    
    # Return compiled data
    return {
        'summary': {
            'total_fees': float(total_fees),
            'total_paid': float(total_paid),
            'total_due': float(total_due),
            'payment_percentage': (float(total_paid) / float(total_fees) * 100) if total_fees > 0 else 0
        },
        'details': details
    }


def _generate_budget_report_data(academic_year, department, start_date, end_date, include_details):
    """Generate budget report data"""
    # Base query
    budgets_query = Budget.objects.filter(academic_year=academic_year)
    allocations_query = BudgetAllocation.objects.filter(budget__academic_year=academic_year)
    
    # For transfers, we need to filter by from_budget and to_budget's academic year
    # since BudgetTransfer doesn't have a direct academic_year field
    transfers_query = BudgetTransfer.objects.filter(
        Q(from_budget__academic_year=academic_year) | 
        Q(to_budget__academic_year=academic_year)
    )
    
    # Apply filters
    if department:
        budgets_query = budgets_query.filter(department=department)
        allocations_query = allocations_query.filter(department=department)
        transfers_query = transfers_query.filter(
            Q(from_budget__department=department) | 
            Q(to_budget__department=department)
        )
    
    if start_date and end_date:
        transfers_query = transfers_query.filter(transfer_date__range=[start_date, end_date])
    
    # Calculate summary data
    total_budget = budgets_query.aggregate(total=Sum('amount'))['total'] or 0
    total_allocated = allocations_query.aggregate(total=Sum('amount'))['total'] or 0
    total_unallocated = total_budget - total_allocated
    total_transfers = transfers_query.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get detailed data if requested
    details = []
    if include_details:
        for budget in budgets_query:
            allocated = allocations_query.filter(budget=budget).aggregate(total=Sum('amount'))['total'] or 0
            details.append({
                'title': budget.title,
                'department': budget.department.name if budget.department else 'N/A',
                'total_amount': float(budget.amount),
                'allocated_amount': float(allocated),
                'unallocated_amount': float(budget.amount) - float(allocated),
                'status': budget.status
            })
    
    # Return compiled data
    return {
        'summary': {
            'total_budget': float(total_budget),
            'total_allocated': float(total_allocated),
            'total_unallocated': float(total_unallocated),
            'total_transfers': float(total_transfers),
            'allocation_percentage': (float(total_allocated) / float(total_budget) * 100) if total_budget > 0 else 0
        },
        'details': details
    }


def _generate_expense_report_data(academic_year, department, start_date, end_date, include_details):
    """Generate expense report data"""
    # Base query
    expenses_query = Expense.objects.filter(academic_year=academic_year, status='paid')
    
    # Apply filters
    if department:
        expenses_query = expenses_query.filter(department=department)
    
    if start_date and end_date:
        expenses_query = expenses_query.filter(date__range=[start_date, end_date])
    
    # Calculate summary data
    total_expenses = expenses_query.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get category breakdown
    category_breakdown = expenses_query.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Get detailed data if requested
    details = []
    if include_details:
        for expense in expenses_query:
            details.append({
                'title': expense.title,
                'category': expense.category.name,
                'department': expense.department.name if expense.department else 'N/A',
                'amount': float(expense.amount),
                'date': expense.date.strftime('%Y-%m-%d'),
                'payment_method': expense.get_payment_method_display() if expense.payment_method else 'N/A'
            })
    
    # Return compiled data
    return {
        'summary': {
            'total_expenses': float(total_expenses),
            'category_breakdown': [
                {'category': item['category__name'], 'amount': float(item['total'])}
                for item in category_breakdown
            ]
        },
        'details': details
    }


def _generate_financial_summary_data(academic_year, department, start_date, end_date, include_details):
    """Generate financial summary report data"""
    # Get data from other reports
    fee_data = _generate_fee_report_data(academic_year, department, start_date, end_date, False)
    budget_data = _generate_budget_report_data(academic_year, department, start_date, end_date, False)
    expense_data = _generate_expense_report_data(academic_year, department, start_date, end_date, False)
    
    # Calculate additional metrics
    total_income = fee_data['summary']['total_paid']
    total_expenses = expense_data['summary']['total_expenses']
    net_balance = total_income - total_expenses
    
    # Return compiled data
    return {
        'summary': {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_balance': net_balance,
            'budget_allocation': budget_data['summary']['total_allocated'],
            'budget_utilization': (total_expenses / budget_data['summary']['total_allocated'] * 100) 
                if budget_data['summary']['total_allocated'] > 0 else 0
        },
        'fee_data': fee_data['summary'],
        'budget_data': budget_data['summary'],
        'expense_data': expense_data['summary']
    }


def _generate_csv_report(report):
    """Generate a CSV report from saved report data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report.title}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Report Title', report.title])
    writer.writerow(['Generated On', report.created_at.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Academic Year', report.academic_year.name])
    if report.department:
        writer.writerow(['Department', report.department.name])
    writer.writerow([])
    
    # Write summary data
    writer.writerow(['Summary'])
    for key, value in report.report_data.get('summary', {}).items():
        writer.writerow([key.replace('_', ' ').title(), value])
    
    # Write detailed data if available
    details = report.report_data.get('details', [])
    if details:
        writer.writerow([])
        writer.writerow(['Detailed Data'])
        
        # Write header row
        if details:
            writer.writerow(details[0].keys())
            
            # Write data rows
            for item in details:
                writer.writerow(item.values())
    
    return response


def _generate_excel_report(report):
    """Generate an Excel report from saved report data"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#DDDDDD'})
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    
    # Write header
    row = 0
    worksheet.write(row, 0, 'Report Title', header_format)
    worksheet.write(row, 1, report.title)
    row += 1
    
    worksheet.write(row, 0, 'Generated On', header_format)
    worksheet.write(row, 1, report.created_at.strftime('%Y-%m-%d %H:%M'))
    row += 1
    
    worksheet.write(row, 0, 'Academic Year', header_format)
    worksheet.write(row, 1, report.academic_year.name)
    row += 1
    
    if report.department:
        worksheet.write(row, 0, 'Department', header_format)
        worksheet.write(row, 1, report.department.name)
        row += 1
    
    row += 1
    
    # Write summary data
    worksheet.write(row, 0, 'Summary', title_format)
    row += 1
    
    for key, value in report.report_data.get('summary', {}).items():
        worksheet.write(row, 0, key.replace('_', ' ').title(), header_format)
        worksheet.write(row, 1, value)
        row += 1
    
    # Write detailed data if available
    details = report.report_data.get('details', [])
    if details:
        row += 2
        worksheet.write(row, 0, 'Detailed Data', title_format)
        row += 1
        
        # Write header row
        if details:
            col = 0
            for key in details[0].keys():
                worksheet.write(row, col, key.replace('_', ' ').title(), header_format)
                col += 1
            row += 1
            
            # Write data rows
            for item in details:
                col = 0
                for value in item.values():
                    worksheet.write(row, col, value)
                    col += 1
                row += 1
    
    workbook.close()
    
    # Prepare response
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report.title}.xlsx"'
    
    return response


def _generate_pdf_report(report):
    """Generate a PDF report from saved report data"""
    buffer = io.BytesIO()
    
    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add report title
    elements.append(Paragraph(report.title, title_style))
    elements.append(Spacer(1, 12))
    
    # Add report metadata
    elements.append(Paragraph(f"Generated On: {report.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(f"Academic Year: {report.academic_year.name}", normal_style))
    if report.department:
        elements.append(Paragraph(f"Department: {report.department.name}", normal_style))
    elements.append(Spacer(1, 12))
    
    # Add summary section
    elements.append(Paragraph("Summary", subtitle_style))
    elements.append(Spacer(1, 6))
    
    # Create summary table
    summary_data = []
    summary_data.append(["Metric", "Value"])
    
    for key, value in report.report_data.get('summary', {}).items():
        formatted_key = key.replace('_', ' ').title()
        formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
        summary_data.append([formatted_key, formatted_value])
    
    summary_table = Table(summary_data, colWidths=[300, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    
    # Add details section if available
    details = report.report_data.get('details', [])
    if details:
        elements.append(Paragraph("Detailed Data", subtitle_style))
        elements.append(Spacer(1, 6))
        
        # Create details table
        details_data = []
        
        # Add header row
        if details:
            header_row = [key.replace('_', ' ').title() for key in details[0].keys()]
            details_data.append(header_row)
            
            # Add data rows
            for item in details:
                row = []
                for value in item.values():
                    if isinstance(value, (int, float)):
                        row.append(f"{value:,.2f}")
                    else:
                        row.append(str(value))
                details_data.append(row)
        
        # Calculate column widths based on number of columns
        num_cols = len(details_data[0])
        col_width = 500 / num_cols
        
        details_table = Table(details_data, colWidths=[col_width] * num_cols)
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(details_table)
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
    
    return response
