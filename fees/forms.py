from django import forms
from django.core.exceptions import ValidationError
from .models import FeeCategory, FeeStructure, StudentFee, FeePayment, FeeDiscount
from users.models import User
from core.models import AcademicYear, Department


class FeeCategoryForm(forms.ModelForm):
    """Form for creating and updating fee categories"""
    class Meta:
        model = FeeCategory
        fields = ['name', 'description', 'is_recurring']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeeStructureForm(forms.ModelForm):
    """Form for creating and updating fee structures"""
    class Meta:
        model = FeeStructure
        fields = ['name', 'category', 'department', 'academic_year', 'amount', 'due_date', 'late_fee', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'late_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        department = cleaned_data.get('department')
        academic_year = cleaned_data.get('academic_year')
        
        # Check for duplicate fee structure
        if category and department and academic_year:
            if FeeStructure.objects.filter(
                category=category,
                department=department,
                academic_year=academic_year
            ).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError("A fee structure with this category, department, and academic year already exists.")
        
        return cleaned_data


class StudentFeeForm(forms.ModelForm):
    """Form for assigning fees to students"""
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(role='student'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = StudentFee
        fields = ['student', 'fee_structure', 'amount', 'due_date', 'waiver_amount', 'waiver_reason']
        widgets = {
            'fee_structure': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'waiver_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'waiver_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        fee_structure = cleaned_data.get('fee_structure')
        waiver_amount = cleaned_data.get('waiver_amount')
        amount = cleaned_data.get('amount')
        
        # Check for duplicate student fee
        if student and fee_structure:
            if StudentFee.objects.filter(
                student=student,
                fee_structure=fee_structure
            ).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError("This fee has already been assigned to this student.")
        
        # Validate waiver amount
        if waiver_amount and amount and waiver_amount > amount:
            raise ValidationError("Waiver amount cannot be greater than the total fee amount.")
        
        return cleaned_data


class BulkFeeAssignmentForm(forms.Form):
    """Form for assigning fees to multiple students at once"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class FeePaymentForm(forms.ModelForm):
    """Form for recording fee payments"""
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(role='student'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = FeePayment
        fields = ['student', 'student_fee', 'academic_year', 'amount', 'payment_method', 
                  'transaction_id', 'receipt_number', 'status', 'remarks']
        widgets = {
            'student_fee': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If student is selected, filter student_fee to show only that student's fees
        if 'student' in self.data:
            try:
                student_id = int(self.data.get('student'))
                self.fields['student_fee'].queryset = StudentFee.objects.filter(
                    student_id=student_id, is_paid=False
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.student:
            self.fields['student_fee'].queryset = StudentFee.objects.filter(
                student=self.instance.student, is_paid=False
            )
        else:
            self.fields['student_fee'].queryset = StudentFee.objects.none()


class FeeDiscountForm(forms.ModelForm):
    """Form for creating and updating fee discounts"""
    class Meta:
        model = FeeDiscount
        fields = ['name', 'description', 'discount_type', 'value', 'academic_year', 'fee_category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'fee_category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        value = cleaned_data.get('value')
        
        # Validate percentage discount
        if discount_type == 'percentage' and value > 100:
            raise ValidationError("Percentage discount cannot be greater than 100%.")
        
        return cleaned_data


class FeeSearchForm(forms.Form):
    """Form for searching fees"""
    student = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
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
    is_paid = forms.ChoiceField(
        choices=[('', 'All'), ('paid', 'Paid'), ('unpaid', 'Unpaid')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
