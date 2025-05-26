from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, AcademicYear, Department
from users.models import User


class BudgetCategory(models.Model):
    """Model for budget categories"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Budget Categories"


class Budget(TimeStampedModel):
    """Model for department budgets"""
    BUDGET_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='budgets')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(BudgetCategory, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=BUDGET_STATUS_CHOICES, default='draft')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_budgets')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.department.name} ({self.academic_year.name})"
    
    def approve(self, approved_by):
        """Approve the budget"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_date = timezone.now()
        self.save()
    
    def reject(self, rejection_reason):
        """Reject the budget"""
        self.status = 'rejected'
        self.rejection_reason = rejection_reason
        self.save()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['department', 'academic_year', 'category']


class BudgetAllocation(TimeStampedModel):
    """Model for budget allocations"""
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='allocations')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_date = models.DateField(default=timezone.now)
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='budget_allocations')
    
    def __str__(self):
        return f"{self.title} - {self.budget.department.name}"
    
    class Meta:
        ordering = ['-allocated_date']


class BudgetTransfer(TimeStampedModel):
    """Model for budget transfers between departments"""
    from_budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transfers_from')
    to_budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transfers_to')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transfer_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transfers')
    approved_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Transfer from {self.from_budget.department.name} to {self.to_budget.department.name}: {self.amount}"
    
    def approve(self, approved_by):
        """Approve the budget transfer"""
        self.approved = True
        self.approved_by = approved_by
        self.approved_date = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['-transfer_date']


class BudgetPrediction(TimeStampedModel):
    """Model for storing AI-generated budget predictions"""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='budget_predictions')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='budget_predictions')
    category = models.ForeignKey(BudgetCategory, on_delete=models.CASCADE, related_name='budget_predictions')
    predicted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    confidence_score = models.FloatField(help_text="Confidence level of the prediction (0-1)")
    factors = models.JSONField(default=dict, help_text="Factors that influenced this prediction")
    is_applied = models.BooleanField(default=False, help_text="Whether this prediction has been applied to create an actual budget")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_predictions')
    
    def __str__(self):
        return f"Budget prediction for {self.department.name} - {self.category.name} ({self.academic_year.name})"
    
    def apply_prediction(self, user):
        """Create a budget based on this prediction"""
        if not self.is_applied:
            budget = Budget.objects.create(
                title=f"AI-Generated Budget for {self.category.name}",
                department=self.department,
                academic_year=self.academic_year,
                category=self.category,
                amount=self.predicted_amount,
                description=f"Automatically generated budget based on AI prediction with {self.confidence_score:.2%} confidence.",
                status='draft',
                submitted_by=user
            )
            self.is_applied = True
            self.save()
            return budget
        return None
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['department', 'academic_year', 'category']
