from django import forms
from django.core.exceptions import ValidationError
from .models import BudgetCategory, Budget, BudgetAllocation, BudgetTransfer
from core.models import Department, AcademicYear


class BudgetCategoryForm(forms.ModelForm):
    """Form for creating and updating budget categories"""
    class Meta:
        model = BudgetCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BudgetForm(forms.ModelForm):
    """Form for creating and updating budgets"""
    class Meta:
        model = Budget
        fields = ['title', 'department', 'academic_year', 'category', 'amount', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        academic_year = cleaned_data.get('academic_year')
        category = cleaned_data.get('category')
        
        # Check for duplicate budget
        if department and academic_year and category:
            if Budget.objects.filter(
                department=department,
                academic_year=academic_year,
                category=category
            ).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError("A budget with this department, academic year, and category already exists.")
        
        return cleaned_data


class BudgetApprovalForm(forms.Form):
    """Form for approving or rejecting budgets"""
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
            raise ValidationError("Please provide a reason for rejecting the budget.")
        
        return cleaned_data


class BudgetAllocationForm(forms.ModelForm):
    """Form for creating and updating budget allocations"""
    class Meta:
        model = BudgetAllocation
        fields = ['budget', 'title', 'description', 'amount', 'allocated_date']
        widgets = {
            'budget': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'allocated_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved budgets for allocation
        self.fields['budget'].queryset = Budget.objects.filter(status='approved')
    
    def clean(self):
        cleaned_data = super().clean()
        budget = cleaned_data.get('budget')
        amount = cleaned_data.get('amount')
        
        if budget and amount:
            # Calculate total allocations for this budget
            total_allocated = BudgetAllocation.objects.filter(budget=budget).exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            # Check if allocation exceeds budget
            if amount + total_allocated > budget.amount:
                raise ValidationError(
                    f"This allocation would exceed the budget limit. "
                    f"Available: {budget.amount - total_allocated}, Requested: {amount}"
                )
        
        return cleaned_data


class BudgetTransferForm(forms.ModelForm):
    """Form for creating and updating budget transfers"""
    class Meta:
        model = BudgetTransfer
        fields = ['from_budget', 'to_budget', 'amount', 'transfer_date', 'reason']
        widgets = {
            'from_budget': forms.Select(attrs={'class': 'form-select'}),
            'to_budget': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'transfer_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved budgets for transfer
        self.fields['from_budget'].queryset = Budget.objects.filter(status='approved')
        self.fields['to_budget'].queryset = Budget.objects.filter(status='approved')
    
    def clean(self):
        cleaned_data = super().clean()
        from_budget = cleaned_data.get('from_budget')
        to_budget = cleaned_data.get('to_budget')
        amount = cleaned_data.get('amount')
        
        if from_budget and to_budget and amount:
            # Check if from_budget and to_budget are the same
            if from_budget == to_budget:
                raise ValidationError("Cannot transfer budget to the same budget.")
            
            # Calculate available amount in from_budget
            total_allocated = BudgetAllocation.objects.filter(budget=from_budget).aggregate(
                total=models.Sum('amount'))['total'] or 0
            total_transfers_out = BudgetTransfer.objects.filter(
                from_budget=from_budget, approved=True
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            total_transfers_in = BudgetTransfer.objects.filter(
                to_budget=from_budget, approved=True
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            available = from_budget.amount - total_allocated - total_transfers_out + total_transfers_in
            
            # Check if transfer exceeds available amount
            if amount > available:
                raise ValidationError(
                    f"This transfer would exceed the available budget. "
                    f"Available: {available}, Requested: {amount}"
                )
        
        return cleaned_data


class BudgetTransferApprovalForm(forms.Form):
    """Form for approving budget transfers"""
    approve = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BudgetSearchForm(forms.Form):
    """Form for searching budgets"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=BudgetCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Budget.BUDGET_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class BudgetPredictionForm(forms.Form):
    """Form for generating budget predictions using AI"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=BudgetCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    include_previous_years = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include data from previous years in the prediction"
    )
    include_expense_trends = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include expense trends in the prediction"
    )
    include_department_growth = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Consider department growth in the prediction"
    )


class BudgetPredictionApplyForm(forms.Form):
    """Form for applying a budget prediction to create an actual budget"""
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="I confirm that I want to create a budget based on this prediction"
    )
    adjust_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Optionally adjust the predicted amount before creating the budget"
    )
    
    def __init__(self, *args, prediction=None, **kwargs):
        super().__init__(*args, **kwargs)
        if prediction:
            self.fields['adjust_amount'].initial = prediction.predicted_amount
