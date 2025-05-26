from django import forms
from django.core.exceptions import ValidationError
from .models import ExpenseCategory, Expense, ExpenseAttachment, RecurringExpense
from core.models import Department, AcademicYear
from budget.models import Budget, BudgetAllocation


class ExpenseCategoryForm(forms.ModelForm):
    """Form for creating and updating expense categories"""
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExpenseForm(forms.ModelForm):
    """Form for creating and updating expenses"""
    class Meta:
        model = Expense
        fields = ['title', 'description', 'amount', 'date', 'category', 'department', 
                  'academic_year', 'budget', 'budget_allocation', 'status', 'receipt']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'budget': forms.Select(attrs={'class': 'form-select'}),
            'budget_allocation': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show approved budgets
        self.fields['budget'].queryset = Budget.objects.filter(status='approved')
        self.fields['budget_allocation'].queryset = BudgetAllocation.objects.none()
        
        # Pre-select department based on user's department if available
        if user and user.department and not self.instance.pk:
            self.fields['department'].initial = user.department
        
        # If budget is selected, filter budget allocations
        if 'budget' in self.data:
            try:
                budget_id = int(self.data.get('budget'))
                self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(budget_id=budget_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.budget:
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(budget=self.instance.budget)
    
    def clean(self):
        cleaned_data = super().clean()
        budget = cleaned_data.get('budget')
        budget_allocation = cleaned_data.get('budget_allocation')
        
        # Ensure budget allocation belongs to the selected budget
        if budget and budget_allocation and budget_allocation.budget != budget:
            raise ValidationError("The selected budget allocation does not belong to the selected budget.")
        
        return cleaned_data


class ExpenseAttachmentForm(forms.ModelForm):
    """Form for adding attachments to expenses"""
    class Meta:
        model = ExpenseAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ExpenseApprovalForm(forms.Form):
    """Form for approving or rejecting expenses"""
    DECISION_CHOICES = (
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    )
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if decision == 'reject' and not rejection_reason:
            raise ValidationError("Please provide a reason for rejecting the expense.")
        
        return cleaned_data


class ExpensePaymentForm(forms.Form):
    """Form for marking expenses as paid"""
    payment_method = forms.ChoiceField(
        choices=Expense.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class RecurringExpenseForm(forms.ModelForm):
    """Form for creating and updating recurring expenses"""
    class Meta:
        model = RecurringExpense
        fields = ['title', 'description', 'amount', 'category', 'department', 'budget',
                  'frequency', 'start_date', 'end_date', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'budget': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show approved budgets
        self.fields['budget'].queryset = Budget.objects.filter(status='approved')
        
        # Pre-select department based on user's department if available
        if user and user.department and not self.instance.pk:
            self.fields['department'].initial = user.department
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if end_date and start_date and end_date < start_date:
            raise ValidationError("End date cannot be earlier than start date.")
        
        # Set next_due_date to start_date for new recurring expenses
        if not self.instance.pk and start_date:
            self.instance.next_due_date = start_date
        
        return cleaned_data


class ExpenseSearchForm(forms.Form):
    """Form for searching expenses"""
    title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Expense.EXPENSE_STATUS_CHOICES),
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
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError("End date cannot be earlier than start date.")
