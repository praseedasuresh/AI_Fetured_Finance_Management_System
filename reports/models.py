from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel, AcademicYear, Department
from users.models import User


class ReportTemplate(TimeStampedModel):
    """Model for storing report templates"""
    REPORT_TYPES = (
        ('fee', 'Fee Report'),
        ('budget', 'Budget Report'),
        ('expense', 'Expense Report'),
        ('financial', 'Financial Summary Report'),
        ('custom', 'Custom Report'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    template_data = models.JSONField(help_text=_("JSON configuration for the report template"))
    is_system = models.BooleanField(default=False, help_text=_("Whether this is a system-defined template"))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['report_type', 'title']


class SavedReport(TimeStampedModel):
    """Model for storing generated reports"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, related_name='saved_reports')
    report_data = models.JSONField(help_text=_("JSON data for the report"))
    parameters = models.JSONField(help_text=_("Parameters used to generate the report"))
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='reports')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='saved_reports')
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']


class ScheduledReport(TimeStampedModel):
    """Model for scheduling automatic report generation"""
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='scheduled_reports')
    parameters = models.JSONField(help_text=_("Parameters to use when generating the report"), default=dict, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    next_run = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    recipients = models.ManyToManyField(User, related_name='subscribed_reports')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='scheduled_reports')
    
    def __str__(self):
        return self.title
    
    def calculate_next_run(self):
        """Calculate the next run date based on frequency"""
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now()
        
        if self.frequency == 'daily':
            # Set to tomorrow at the same time
            self.next_run = now + timedelta(days=1)
        elif self.frequency == 'weekly':
            # Set to next week at the same time
            self.next_run = now + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Set to next month at the same time
            self.next_run = now + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            # Set to next quarter at the same time
            self.next_run = now + relativedelta(months=3)
        else:
            # Default to tomorrow
            self.next_run = now + timedelta(days=1)
        
        return self.next_run
    
    class Meta:
        ordering = ['next_run']
