from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import FeePayment, StudentFee

# This file is intentionally created to handle signals for the fees app.
# It's referenced in FeesConfig.ready() method.

@receiver(post_save, sender=FeePayment)
def update_student_fee_status(sender, instance, created, **kwargs):
    """
    Update the status of a StudentFee when a payment is made
    """
    if created or instance.is_approved:
        student_fee = instance.student_fee
        
        # Calculate total paid amount
        total_paid = FeePayment.objects.filter(
            student_fee=student_fee,
            is_approved=True
        ).exclude(id=instance.id if not instance.is_approved else None).sum('amount')
        
        # Add current payment if approved
        if instance.is_approved:
            total_paid += instance.amount
        
        # Update student fee status based on payment
        if total_paid >= student_fee.amount:
            student_fee.status = 'paid'
        elif total_paid > 0:
            student_fee.status = 'partial'
        else:
            student_fee.status = 'pending'
        
        student_fee.save()
