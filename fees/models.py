from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, AcademicYear, Department, Course
from users.models import User


class FeeCategory(models.Model):
    """Model for fee categories"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_recurring = models.BooleanField(default=True, help_text="Whether this fee is charged regularly")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Fee Categories"


class FeeStructure(TimeStampedModel):
    """Model for fee structures"""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='fee_structures')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='fee_structures')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='fee_structures')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.department.name} ({self.academic_year.name})"
    
    class Meta:
        ordering = ['-academic_year__start_date', 'due_date']
        unique_together = ['category', 'department', 'academic_year']


class StudentFee(TimeStampedModel):
    """Model for assigning fees to students"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_fees')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='student_fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    waiver_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, 
                                      help_text="Amount waived from the fee")
    waiver_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.fee_structure.name}"
    
    @property
    def is_overdue(self):
        return not self.is_paid and self.due_date < timezone.now().date()
    
    @property
    def payable_amount(self):
        return self.amount - self.waiver_amount
    
    class Meta:
        ordering = ['-due_date']
        unique_together = ['student', 'fee_structure']


class FeePayment(TimeStampedModel):
    """Model for fee payments"""
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('online_payment', 'Online Payment'),
        ('check', 'Check'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fee_payments')
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='fee_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='collected_payments')
    
    def __str__(self):
        return f"Payment #{self.receipt_number} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # If this is a successful payment and linked to a student fee, mark the fee as paid
        if self.status == 'paid' and self.student_fee:
            self.student_fee.is_paid = True
            self.student_fee.save()
        
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-payment_date']


class FeeDiscount(TimeStampedModel):
    """Model for fee discounts"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=(
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ))
    value = models.DecimalField(max_digits=10, decimal_places=2, 
                              help_text="Percentage or fixed amount based on discount type")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='fee_discounts')
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='discounts')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
