from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import ExpenseCategory, Expense, ExpenseAttachment, RecurringExpense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(ImportExportModelAdmin):
    """Admin interface for ExpenseCategory model"""
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


class ExpenseAttachmentInline(admin.TabularInline):
    """Inline admin for ExpenseAttachment model"""
    model = ExpenseAttachment
    extra = 1


@admin.register(Expense)
class ExpenseAdmin(ImportExportModelAdmin):
    """Admin interface for Expense model"""
    list_display = ('title', 'amount', 'date', 'category', 'department', 'academic_year', 'status')
    list_filter = ('status', 'category', 'department', 'academic_year', 'date')
    search_fields = ('title', 'description', 'submitted_by__username', 'submitted_by__email')
    readonly_fields = ('created_at', 'updated_at', 'submitted_by', 'approved_by', 'approved_date')
    date_hierarchy = 'date'
    inlines = [ExpenseAttachmentInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'amount', 'date', 'receipt')
        }),
        ('Classification', {
            'fields': ('category', 'department', 'academic_year', 'budget', 'budget_allocation')
        }),
        ('Status Information', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_reference', 'payment_date')
        }),
        ('System Information', {
            'fields': ('submitted_by', 'approved_by', 'approved_date', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save_model to set submitted_by if not set"""
        if not change and not obj.submitted_by:
            obj.submitted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for ExpenseAttachment model"""
    list_display = ('expense', 'description', 'file')
    list_filter = ('expense__category', 'expense__department')
    search_fields = ('description', 'expense__title')


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(ImportExportModelAdmin):
    """Admin interface for RecurringExpense model"""
    list_display = ('title', 'amount', 'category', 'department', 'frequency', 'next_due_date', 'is_active')
    list_filter = ('is_active', 'frequency', 'category', 'department')
    search_fields = ('title', 'description', 'created_by__username', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    date_hierarchy = 'next_due_date'
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'amount')
        }),
        ('Classification', {
            'fields': ('category', 'department', 'budget')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_due_date', 'is_active')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save_model to set created_by if not set"""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
