from django.contrib import admin
from .models import AcademicYear, Department, Course


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    def save_model(self, request, obj, form, change):
        # If this academic year is being set as active, deactivate all others
        if obj.is_active:
            AcademicYear.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'credits')
    list_filter = ('department', 'credits')
    search_fields = ('name', 'code')
