from django import forms
from .models import AcademicYear, Department, Course


class AcademicYearForm(forms.ModelForm):
    """Form for creating and editing academic years"""
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        # If setting this year as active, deactivate other active years
        if is_active and not self.instance.pk:
            AcademicYear.objects.filter(is_active=True).update(is_active=False)
        elif is_active and self.instance.pk:
            AcademicYear.objects.exclude(pk=self.instance.pk).filter(is_active=True).update(is_active=False)
        
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    """Form for creating and editing departments"""
    class Meta:
        model = Department
        fields = ['name', 'code', 'head', 'description', 'is_active']
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # Check if code exists for another department
            if Department.objects.exclude(pk=self.instance.pk if self.instance.pk else None).filter(code=code).exists():
                raise forms.ValidationError("A department with this code already exists.")
        return code


class CourseForm(forms.ModelForm):
    """Form for creating and editing courses"""
    class Meta:
        model = Course
        fields = ['name', 'code', 'department', 'credits', 'description', 'is_active']
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # Check if code exists for another course
            if Course.objects.exclude(pk=self.instance.pk if self.instance.pk else None).filter(code=code).exists():
                raise forms.ValidationError("A course with this code already exists.")
        return code
