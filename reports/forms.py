from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
import json

from .models import ReportTemplate, SavedReport, ScheduledReport
from core.models import AcademicYear, Department
from users.models import User


class ReportTemplateForm(forms.ModelForm):
    """Form for creating and updating report templates"""
    class Meta:
        model = ReportTemplate
        fields = ['title', 'description', 'report_type', 'template_data']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'template_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
    
    def clean_template_data(self):
        """Validate that template_data is valid JSON"""
        template_data = self.cleaned_data.get('template_data')
        try:
            if isinstance(template_data, str):
                json.loads(template_data)
            return template_data
        except ValueError:
            raise ValidationError("Invalid JSON format for template data")


class SavedReportForm(forms.ModelForm):
    """Form for creating and updating saved reports"""
    class Meta:
        model = SavedReport
        fields = ['title', 'description', 'template', 'academic_year', 'department']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter templates based on user access
        if user and not user.is_superuser and user.role != 'admin':
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                models.Q(is_system=True) | models.Q(created_by=user)
            )
        
        # Pre-select active academic year
        if not self.instance.pk:
            self.fields['academic_year'].initial = AcademicYear.get_active()
            
            # Pre-select department based on user's department if available
            if user and user.department:
                self.fields['department'].initial = user.department


class ScheduledReportForm(forms.ModelForm):
    """Form for creating and updating scheduled reports"""
    recipients_list = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ScheduledReport
        fields = ['title', 'description', 'template', 'frequency', 'next_run', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'next_run': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter templates based on user access
        if user and not user.is_superuser and user.role != 'admin':
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                models.Q(is_system=True) | models.Q(created_by=user)
            )
        
        # Set initial values for new scheduled reports
        if not self.instance.pk:
            self.fields['next_run'].initial = timezone.now()
            self.fields['is_active'].initial = True
        else:
            # For existing reports, initialize recipients_list
            self.fields['recipients_list'].initial = self.instance.recipients.all()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Handle recipients (many-to-many relationship)
            instance.recipients.clear()
            for recipient in self.cleaned_data.get('recipients_list', []):
                instance.recipients.add(recipient)
            
        return instance


class ReportGenerationForm(forms.Form):
    """Form for generating reports"""
    template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    format = forms.ChoiceField(
        choices=[('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')],
        initial='pdf',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter templates based on user access
        if user and not user.is_superuser and user.role != 'admin':
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                models.Q(is_system=True) | models.Q(created_by=user)
            )
        
        # Set initial values
        self.fields['academic_year'].initial = AcademicYear.get_active()
        
        # Pre-select department based on user's department if available
        if user and user.department:
            self.fields['department'].initial = user.department
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError("End date cannot be earlier than start date.")
        
        return cleaned_data
