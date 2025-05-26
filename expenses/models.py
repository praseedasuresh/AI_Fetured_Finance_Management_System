from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, AcademicYear, Department
from users.models import User
from budget.models import Budget, BudgetAllocation


class ExpenseCategory(models.Model):
    """Model for expense categories"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Expense Categories"


class Expense(TimeStampedModel):
    """Model for tracking expenses"""
    EXPENSE_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('check', 'Check'),
        ('online_payment', 'Online Payment'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='expenses')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='expenses')
    budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    budget_allocation = models.ForeignKey(BudgetAllocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    status = models.CharField(max_length=20, choices=EXPENSE_STATUS_CHOICES, default='draft')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_expenses')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.amount}"
    
    def approve(self, approved_by):
        """Approve the expense"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_date = timezone.now()
        self.save()
    
    def reject(self, rejection_reason):
        """Reject the expense"""
        self.status = 'rejected'
        self.rejection_reason = rejection_reason
        self.save()
    
    def mark_as_paid(self, payment_method, payment_reference=None, payment_date=None):
        """Mark the expense as paid"""
        self.status = 'paid'
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.payment_date = payment_date or timezone.now().date()
        self.save()
    
    class Meta:
        ordering = ['-date']


class ExpenseAttachment(TimeStampedModel):
    """Model for expense attachments"""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='expense_attachments/')
    description = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Attachment for {self.expense.title}"


class RecurringExpense(TimeStampedModel):
    """Model for recurring expenses"""
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='recurring_expenses')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='recurring_expenses')
    budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_expenses')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_recurring_expenses')
    
    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()})"
    
    def update_next_due_date(self):
        """Update the next due date based on frequency"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if not self.is_active:
            return
        
        if self.end_date and self.next_due_date > self.end_date:
            self.is_active = False
            self.save()
            return
        
        current_date = self.next_due_date
        
        if self.frequency == 'daily':
            self.next_due_date = current_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_due_date = current_date + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            self.next_due_date = current_date + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            self.next_due_date = current_date + relativedelta(months=3)
        elif self.frequency == 'yearly':
            self.next_due_date = current_date + relativedelta(years=1)
        
        self.save()
    
    def create_expense(self):
        """Create an expense from this recurring expense"""
        if not self.is_active:
            return None
        
        current_academic_year = AcademicYear.get_active()
        if not current_academic_year:
            return None
        
        expense = Expense.objects.create(
            title=self.title,
            description=f"Recurring expense: {self.description}",
            amount=self.amount,
            date=self.next_due_date,
            category=self.category,
            department=self.department,
            academic_year=current_academic_year,
            budget=self.budget,
            status='submitted',
            submitted_by=self.created_by
        )
        
        self.update_next_due_date()
        return expense
    
    class Meta:
        ordering = ['next_due_date']
