from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, Q, Count
from django.utils import timezone
import json
import time
import openai
import logging

from .models import ChatSession, ChatMessage, FinancialQuery, ExpenseAnomaly
from users.decorators import finance_staff_required
from budget.models import Budget, BudgetAllocation, BudgetTransfer
from expenses.models import Expense, ExpenseCategory
from fees.models import FeePayment, StudentFee
from core.models import AcademicYear, Department

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
def get_openai_client():
    """Get a properly initialized OpenAI client with the current API key"""
    try:
        # Always get a fresh client with the current API key
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        return None


@login_required
def chat_dashboard(request):
    """View for the AI assistant chat dashboard"""
    # Get user's active chat sessions
    chat_sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    
    # Get recent financial queries
    recent_queries = FinancialQuery.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    return render(request, 'ai_assistant/dashboard.html', {
        'chat_sessions': chat_sessions,
        'recent_queries': recent_queries,
    })


@login_required
def chat_session(request, session_id=None):
    """View for a specific chat session"""
    # Get or create chat session
    if session_id:
        session = get_object_or_404(ChatSession, pk=session_id, user=request.user)
    else:
        session = ChatSession.objects.create(
            user=request.user,
            title=f"New Chat ({timezone.now().strftime('%Y-%m-%d %H:%M')})"
        )
        # Add a welcome message
        ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content="Hello! I'm your Finance Assistant. How can I help you today? You can ask me about expenses, budgets, or financial reports."
        )
    
    # Get messages for this session
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
    
    return render(request, 'ai_assistant/chat_session.html', {
        'session': session,
        'messages': messages,
    })


@csrf_exempt
@login_required
def chat_message_api(request, session_id):
    """API endpoint for sending/receiving chat messages"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    session = get_object_or_404(ChatSession, pk=session_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Save user message
        ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=user_message
        )
        
        # Process the query and generate a response
        start_time = time.time()
        response_text = process_financial_query(request.user, user_message)
        execution_time = time.time() - start_time
        
        # Save the query for analytics
        FinancialQuery.objects.create(
            user=request.user,
            query_text=user_message,
            result_summary=response_text[:500],  # Save first 500 chars of response
            execution_time=execution_time
        )
        
        # Save assistant response
        assistant_message = ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=response_text
        )
        
        return JsonResponse({
            'id': assistant_message.id,
            'content': assistant_message.content,
            'timestamp': assistant_message.created_at.isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error in chat_message_api: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def process_financial_query(user, query):
    """Process a financial query and return a response"""
    try:
        # Get a fresh client for each request
        openai_client = get_openai_client()
        
        if not openai_client:
            return "Sorry, the AI assistant is currently unavailable. Please contact your administrator to verify the OpenAI API key configuration."
        
        # Get financial context based on user's role
        financial_context = get_financial_context(user)
        
        # Prepare the messages for OpenAI
        messages = [
            {"role": "system", "content": f"""You are a helpful financial assistant for a Finance Management System. 
            You have access to the following financial data: {financial_context}
            
            Answer questions about the financial data in a helpful, concise manner.
            If you don't know the answer, say so rather than making up information.
            Format your responses using markdown for better readability."""},
            {"role": "user", "content": query}
        ]
        
        # Call OpenAI API
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",  # Use an appropriate model
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
            )
            
            return response.choices[0].message.content
        except Exception as api_error:
            logger.error(f"OpenAI API error: {str(api_error)}")
            return f"I encountered an error while processing your question. Please try again with a different question or contact your administrator. Error details: {str(api_error)}"
        
    except Exception as e:
        logger.error(f"Error processing financial query: {str(e)}")
        return f"Sorry, I encountered an error while processing your query: {str(e)}"


def get_financial_context(user):
    """Get relevant financial context based on user's role and permissions"""
    context = {}
    
    try:
        # Get current academic year for context
        current_year = AcademicYear.get_active()
        if current_year:
            context['current_academic_year'] = current_year.name
        
        # Different context for different user roles
        if user.is_superuser or user.role in ['admin', 'finance_staff']:
            # Get budget summary
            budgets = Budget.objects.all()
            total_budget = budgets.aggregate(total=Sum('amount'))['total'] or 0
            
            # Get department-wise budget breakdown
            department_budgets = {}
            for dept in Department.objects.all():
                dept_budget = Budget.objects.filter(department=dept).aggregate(total=Sum('amount'))['total'] or 0
                department_budgets[dept.name] = float(dept_budget)
            
            # Get expense summary
            expenses = Expense.objects.all()
            total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
            
            # Get expense categories breakdown
            category_expenses = {}
            for category in ExpenseCategory.objects.all():
                cat_expenses = Expense.objects.filter(category=category).aggregate(total=Sum('amount'))['total'] or 0
                category_expenses[category.name] = float(cat_expenses)
            
            # Get monthly expense trend (last 6 months)
            import datetime
            today = datetime.date.today()
            six_months_ago = today - datetime.timedelta(days=180)
            monthly_expenses = {}
            for i in range(6):
                month_start = today.replace(day=1) - datetime.timedelta(days=30*i)
                month_end = (month_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                month_name = month_start.strftime('%B %Y')
                month_expenses = Expense.objects.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
                monthly_expenses[month_name] = float(month_expenses)
            
            # Get fee payment summary
            payments = FeePayment.objects.all()
            total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0
            
            # Get pending fees
            pending_fees = StudentFee.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
            
            # Compile all data for admin/finance staff
            context = {
                'current_academic_year': current_year.name if current_year else 'Not set',
                'total_budget': float(total_budget),
                'department_budgets': department_budgets,
                'total_expenses': float(total_expenses),
                'category_expenses': category_expenses,
                'monthly_expense_trend': monthly_expenses,
                'total_payments': float(total_payments),
                'pending_fees': float(pending_fees),
                'budget_count': budgets.count(),
                'expense_count': expenses.count(),
                'recent_expenses': list(expenses.order_by('-date')[:5].values('title', 'amount', 'date', 'department__name')),
                'budget_utilization': float(total_expenses) / float(total_budget) * 100 if total_budget > 0 else 0,
            }
            
        elif user.role == 'faculty':
            # For faculty, only show their department's data
            department = user.department
            if department:
                dept_budgets = Budget.objects.filter(department=department)
                dept_expenses = Expense.objects.filter(department=department)
                dept_budget_total = dept_budgets.aggregate(total=Sum('amount'))['total'] or 0
                dept_expense_total = dept_expenses.aggregate(total=Sum('amount'))['total'] or 0
                
                # Get monthly expense trend for department (last 3 months)
                import datetime
                today = datetime.date.today()
                monthly_expenses = {}
                for i in range(3):
                    month_start = today.replace(day=1) - datetime.timedelta(days=30*i)
                    month_end = (month_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                    month_name = month_start.strftime('%B %Y')
                    month_expenses = dept_expenses.filter(date__range=[month_start, month_end]).aggregate(total=Sum('amount'))['total'] or 0
                    monthly_expenses[month_name] = float(month_expenses)
                
                context = {
                    'department_name': department.name,
                    'department_budget': float(dept_budget_total),
                    'department_expenses': float(dept_expense_total),
                    'monthly_expense_trend': monthly_expenses,
                    'budget_utilization': float(dept_expense_total) / float(dept_budget_total) * 100 if dept_budget_total > 0 else 0,
                    'recent_dept_expenses': list(dept_expenses.order_by('-date')[:5].values('title', 'amount', 'date')),
                }
        
        elif user.role == 'student':
            # For students, only show their fee payment data
            try:
                student_profile = user.student_profile
                student_fees = StudentFee.objects.filter(student=user)
                student_payments = FeePayment.objects.filter(student=user)
                
                total_fees = student_fees.aggregate(total=Sum('amount'))['total'] or 0
                total_paid = student_payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
                
                context = {
                    'student_name': user.get_full_name(),
                    'total_fees': float(total_fees),
                    'total_fees_paid': float(total_paid),
                    'pending_amount': float(total_fees) - float(total_paid),
                    'payment_status': 'Fully Paid' if total_paid >= total_fees else 'Partially Paid' if total_paid > 0 else 'Not Paid',
                    'recent_payments': list(student_payments.order_by('-payment_date')[:3].values('receipt_number', 'amount', 'payment_date')),
                }
            except:
                context = {'error': 'No student profile found'}
    
    except Exception as e:
        logger.error(f"Error getting financial context: {str(e)}")
        context = {'error': str(e)}
    
    return context


@login_required
@finance_staff_required
def anomaly_detection_dashboard(request):
    """Dashboard for expense anomaly detection"""
    # Get anomalies, with most recent first
    anomalies = ExpenseAnomaly.objects.select_related('expense', 'expense__department', 'expense__category').order_by('-created_at')
    
    # Filter by review status if requested
    review_status = request.GET.get('review_status')
    if review_status == 'reviewed':
        anomalies = anomalies.filter(is_reviewed=True)
    elif review_status == 'unreviewed':
        anomalies = anomalies.filter(is_reviewed=False)
    
    # Filter by anomaly type if requested
    anomaly_type = request.GET.get('anomaly_type')
    if anomaly_type and anomaly_type != 'all':
        anomalies = anomalies.filter(anomaly_type=anomaly_type)
    
    # Get statistics
    total_anomalies = ExpenseAnomaly.objects.count()
    unreviewed_anomalies = ExpenseAnomaly.objects.filter(is_reviewed=False).count()
    false_positives = ExpenseAnomaly.objects.filter(is_false_positive=True).count()
    
    # Group by type
    anomaly_types = ExpenseAnomaly.objects.values('anomaly_type').annotate(count=Count('id')).order_by('-count')
    
    return render(request, 'ai_assistant/anomaly_dashboard.html', {
        'anomalies': anomalies,
        'total_anomalies': total_anomalies,
        'unreviewed_anomalies': unreviewed_anomalies,
        'false_positives': false_positives,
        'anomaly_types': anomaly_types,
        'selected_type': anomaly_type,
        'selected_status': review_status,
    })


@login_required
@finance_staff_required
def anomaly_detail(request, anomaly_id):
    """View for a specific anomaly"""
    anomaly = get_object_or_404(ExpenseAnomaly, pk=anomaly_id)
    
    if request.method == 'POST':
        # Handle review actions
        action = request.POST.get('action')
        
        if action == 'mark_reviewed':
            anomaly.is_reviewed = True
            anomaly.is_false_positive = False
            anomaly.reviewed_by = request.user
            anomaly.reviewed_at = timezone.now()
            anomaly.save()
            return redirect('anomaly_detail', anomaly_id=anomaly.id)
            
        elif action == 'mark_false_positive':
            anomaly.is_reviewed = True
            anomaly.is_false_positive = True
            anomaly.reviewed_by = request.user
            anomaly.reviewed_at = timezone.now()
            anomaly.save()
            return redirect('anomaly_detail', anomaly_id=anomaly.id)
    
    # Get related expenses from same department for context
    related_expenses = Expense.objects.filter(
        department=anomaly.expense.department
    ).exclude(
        id=anomaly.expense.id
    ).order_by('-date')[:5]
    
    return render(request, 'ai_assistant/anomaly_detail.html', {
        'anomaly': anomaly,
        'related_expenses': related_expenses,
    })


@login_required
@finance_staff_required
def run_anomaly_detection(request):
    """Run anomaly detection manually"""
    if request.method == 'POST':
        days = int(request.POST.get('days_lookback', 90))
        confidence = float(request.POST.get('min_confidence', 0.7))
        
        # Run the detection algorithm
        from .anomaly_detection import detect_expense_anomalies
        new_anomalies = detect_expense_anomalies(days_lookback=days, min_confidence=confidence)
        
        messages.success(request, f"Anomaly detection completed. {new_anomalies} new anomalies detected.")
        return redirect('anomaly_dashboard')
    
    return render(request, 'ai_assistant/run_anomaly_detection.html')
