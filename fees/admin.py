from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import FeeCategory, FeeStructure, StudentFee, FeePayment, FeeDiscount


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_recurring')
    search_fields = ('name',)
    list_filter = ('is_recurring',)


@admin.register(FeeStructure)
class FeeStructureAdmin(ImportExportModelAdmin):
    list_display = ('name', 'category', 'department', 'academic_year', 'amount', 'due_date', 'is_active')
    list_filter = ('category', 'department', 'academic_year', 'is_active')
    search_fields = ('name',)
    date_hierarchy = 'due_date'


@admin.register(StudentFee)
class StudentFeeAdmin(ImportExportModelAdmin):
    list_display = ('student', 'fee_structure', 'amount', 'due_date', 'is_paid', 'waiver_amount')
    list_filter = ('is_paid', 'fee_structure__category', 'fee_structure__academic_year')
    search_fields = ('student__first_name', 'student__last_name', 'student__email', 'student__student_id')
    date_hierarchy = 'due_date'
    raw_id_fields = ('student', 'fee_structure')


@admin.register(FeePayment)
class FeePaymentAdmin(ImportExportModelAdmin):
    list_display = ('receipt_number', 'student', 'amount', 'payment_date', 'payment_method', 'status')
    list_filter = ('status', 'payment_method', 'academic_year')
    search_fields = ('receipt_number', 'student__first_name', 'student__last_name', 'student__email', 'student__student_id')
    date_hierarchy = 'payment_date'
    raw_id_fields = ('student', 'student_fee', 'collected_by')


@admin.register(FeeDiscount)
class FeeDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'value', 'fee_category', 'academic_year', 'is_active')
    list_filter = ('discount_type', 'fee_category', 'academic_year', 'is_active')
    search_fields = ('name',)
