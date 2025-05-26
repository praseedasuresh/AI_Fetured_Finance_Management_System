from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import Expense, RecurringExpense
from budget.models import BudgetAllocation

# This file is intentionally created to handle signals for the expenses app.
# It's referenced in ExpensesConfig.ready() method.

@receiver(post_save, sender=Expense)
def update_budget_allocation_after_expense(sender, instance, created, **kwargs):
    """
    Update the budget allocation's used amount when an expense is saved
    """
    if instance.budget_allocation and instance.status == 'approved':
        allocation = instance.budget_allocation
        
        # Calculate total expenses for this allocation
        total_expenses = Expense.objects.filter(
            budget_allocation=allocation,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Update allocation's used amount
        allocation.used_amount = total_expenses
        allocation.save(update_fields=['used_amount'])

@receiver(post_delete, sender=Expense)
def update_budget_allocation_after_expense_delete(sender, instance, **kwargs):
    """
    Update the budget allocation's used amount when an expense is deleted
    """
    if instance.budget_allocation and instance.status == 'approved':
        allocation = instance.budget_allocation
        
        # Calculate total expenses for this allocation
        total_expenses = Expense.objects.filter(
            budget_allocation=allocation,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Update allocation's used amount
        allocation.used_amount = total_expenses
        allocation.save(update_fields=['used_amount'])

@receiver(post_save, sender=Expense)
def update_expense_status(sender, instance, created, **kwargs):
    """
    Update the expense status based on approval
    """
    if created:
        # For new expenses, check if auto-approval is needed
        if instance.amount <= 1000:  # Auto-approve small expenses
            instance.status = 'approved'
            instance.save(update_fields=['status'])
