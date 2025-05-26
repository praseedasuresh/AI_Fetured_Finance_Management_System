from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.core.paginator import Paginator

from users.models import User
from fees.models import FeePayment
from expenses.models import Expense
from budget.models import Budget
from .models import AcademicYear, Department, Course
from .forms import AcademicYearForm, DepartmentForm, CourseForm
from users.decorators import admin_required


@login_required
def dashboard(request):
    """Main dashboard view for the finance management system"""
    # Get counts for overview
    students_count = User.objects.filter(role='student').count()
    staff_count = User.objects.filter(role__in=['admin', 'finance_staff', 'faculty']).count()
    departments_count = Department.objects.count()
    
    # Get financial summaries
    current_year = AcademicYear.get_active()
    
    # Calculate fee collection statistics
    total_fees_collected = FeePayment.objects.filter(
        status='paid',
        academic_year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    recent_payments = FeePayment.objects.filter(
        status='paid'
    ).order_by('-payment_date')[:5]
    
    # Calculate expense statistics
    total_expenses = Expense.objects.filter(
        date__range=[current_year.start_date, current_year.end_date] if current_year else [timezone.now().date(), timezone.now().date()]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    recent_expenses = Expense.objects.order_by('-date')[:5]
    
    # Calculate budget statistics
    total_budget = Budget.objects.filter(
        academic_year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    budget_utilization = (total_expenses / total_budget * 100) if total_budget > 0 else 0
    
    context = {
        'students_count': students_count,
        'staff_count': staff_count,
        'departments_count': departments_count,
        'total_fees_collected': total_fees_collected,
        'total_expenses': total_expenses,
        'total_budget': total_budget,
        'budget_utilization': budget_utilization,
        'recent_payments': recent_payments,
        'recent_expenses': recent_expenses,
        'current_year': current_year,
    }
    
    return render(request, 'core/dashboard.html', context)


def home(request):
    """Home page view - redirects to dashboard if logged in"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


# Academic Year Views
@admin_required
def academic_year_list(request):
    """View for listing academic years"""
    academic_years = AcademicYear.objects.all().order_by('-start_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        academic_years = academic_years.filter(name__icontains=search_query)
    
    # Pagination
    paginator = Paginator(academic_years, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/academic_year/list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


@admin_required
def academic_year_create(request):
    """View for creating a new academic year"""
    if request.method == 'POST':
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            academic_year = form.save()
            messages.success(request, 'Academic year created successfully!')
            return redirect('academic_year_list')
    else:
        form = AcademicYearForm()
    
    return render(request, 'core/academic_year/form.html', {
        'form': form,
        'title': 'Create Academic Year'
    })


@admin_required
def academic_year_update(request, pk):
    """View for updating an academic year"""
    academic_year = get_object_or_404(AcademicYear, pk=pk)
    
    if request.method == 'POST':
        form = AcademicYearForm(request.POST, instance=academic_year)
        if form.is_valid():
            form.save()
            messages.success(request, 'Academic year updated successfully!')
            return redirect('academic_year_list')
    else:
        form = AcademicYearForm(instance=academic_year)
    
    return render(request, 'core/academic_year/form.html', {
        'form': form,
        'academic_year': academic_year,
        'title': 'Update Academic Year'
    })


@admin_required
def academic_year_delete(request, pk):
    """View for deleting an academic year"""
    academic_year = get_object_or_404(AcademicYear, pk=pk)
    
    if request.method == 'POST':
        try:
            academic_year.delete()
            messages.success(request, 'Academic year deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting academic year: {str(e)}')
        return redirect('academic_year_list')
    
    return render(request, 'core/academic_year/delete.html', {
        'academic_year': academic_year
    })


# Department Views
@admin_required
def department_list(request):
    """View for listing departments"""
    # Use values() to avoid the head field error until migrations are run
    departments = Department.objects.all().order_by('name').values('id', 'name', 'code', 'description', 'is_active')
    
    # Convert to list for template rendering
    departments_list = list(departments)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        departments_list = [d for d in departments_list if search_query.lower() in d['name'].lower() or search_query.lower() in d['code'].lower()]
    
    # Pagination
    paginator = Paginator(departments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/department/list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


@admin_required
def department_create(request):
    """View for creating a new department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            messages.success(request, 'Department created successfully!')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    
    return render(request, 'core/department/form.html', {
        'form': form,
        'title': 'Create Department'
    })


@admin_required
def department_update(request, pk):
    """View for updating a department"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully!')
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    
    return render(request, 'core/department/form.html', {
        'form': form,
        'department': department,
        'title': 'Update Department'
    })


@admin_required
def department_delete(request, pk):
    """View for deleting a department"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        try:
            department.delete()
            messages.success(request, 'Department deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting department: {str(e)}')
        return redirect('department_list')
    
    return render(request, 'core/department/delete.html', {
        'department': department
    })


# Course Views
@admin_required
def course_list(request):
    """View for listing courses"""
    # Use a raw query or values() to avoid the department.head field error
    courses = Course.objects.all().order_by('code')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(name__icontains=search_query) | courses.filter(code__icontains=search_query)
    
    # Department filter
    department_id = request.GET.get('department')
    if department_id:
        courses = courses.filter(department_id=department_id)
    
    # Get course data without relying on department model fields that might not exist yet
    course_list = []
    for course in courses:
        try:
            # Create a dictionary with dot-accessible attributes
            from types import SimpleNamespace
            course_data = SimpleNamespace(
                id=course.id,
                name=course.name,
                code=course.code,
                credits=course.credits,
                description=course.description,
                is_active=course.is_active,
                department_id=course.department_id,
                department_name=course.department.name
            )
            course_list.append(course_data)
        except:
            # Skip courses with errors
            continue
    
    # Pagination
    paginator = Paginator(course_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get departments for filter (using values to avoid head field)
    departments = Department.objects.all().values('id', 'name')
    
    return render(request, 'core/course/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'departments': departments,
        'selected_department': department_id
    })


@admin_required
def course_create(request):
    """View for creating a new course"""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, 'Course created successfully!')
            return redirect('course_list')
    else:
        form = CourseForm()
    
    return render(request, 'core/course/form.html', {
        'form': form,
        'title': 'Create Course'
    })


@admin_required
def course_update(request, pk):
    """View for updating a course"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'core/course/form.html', {
        'form': form,
        'course': course,
        'title': 'Update Course'
    })


@admin_required
def course_delete(request, pk):
    """View for deleting a course"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        try:
            course.delete()
            messages.success(request, 'Course deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting course: {str(e)}')
        return redirect('course_list')
    
    return render(request, 'core/course/delete.html', {
        'course': course
    })
