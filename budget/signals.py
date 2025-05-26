from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import Budget, BudgetAllocation, BudgetTransfer

# This file is intentionally created to handle signals for the budget app.
# It's referenced in BudgetConfig.ready() method.

@receiver(post_save, sender=BudgetAllocation)
def update_budget_allocation_status(sender, instance, created, **kwargs):
    """
    Update the budget allocation status when a budget allocation is saved
    """
    budget = instance.budget
    
    # Calculate total allocated amount
    total_allocated = BudgetAllocation.objects.filter(
        budget=budget
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Update budget allocated_amount field
    budget.allocated_amount = total_allocated
    budget.save(update_fields=['allocated_amount'])

@receiver(post_delete, sender=BudgetAllocation)
def update_budget_allocation_on_delete(sender, instance, **kwargs):
    """
    Update the budget allocation status when a budget allocation is deleted
    """
    budget = instance.budget
    
    # Calculate total allocated amount
    total_allocated = BudgetAllocation.objects.filter(
        budget=budget
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Update budget allocated_amount field
    budget.allocated_amount = total_allocated
    budget.save(update_fields=['allocated_amount'])

@receiver(post_save, sender=BudgetTransfer)
def update_allocations_after_transfer(sender, instance, created, **kwargs):
    """
    Update the source and destination allocations after a transfer
    """
    if created and instance.status == 'approved':
        # Update source allocation
        source = instance.source_allocation
        source.amount -= instance.amount
        source.save(update_fields=['amount'])
        
        # Update destination allocation
        destination = instance.destination_allocation
        destination.amount += instance.amount
        destination.save(update_fields=['amount'])
