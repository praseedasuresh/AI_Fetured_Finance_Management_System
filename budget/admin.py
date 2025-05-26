from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import BudgetCategory, Budget, BudgetAllocation, BudgetTransfer


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Budget)
class BudgetAdmin(ImportExportModelAdmin):
    list_display = ('title', 'department', 'academic_year', 'category', 'amount', 'status')
    list_filter = ('status', 'department', 'academic_year', 'category')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    raw_id_fields = ('submitted_by', 'approved_by')
    readonly_fields = ('approved_date',)


@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(ImportExportModelAdmin):
    list_display = ('title', 'budget', 'amount', 'allocated_date', 'allocated_by')
    list_filter = ('budget__department', 'budget__academic_year', 'allocated_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'allocated_date'
    raw_id_fields = ('budget', 'allocated_by')


@admin.register(BudgetTransfer)
class BudgetTransferAdmin(ImportExportModelAdmin):
    list_display = ('from_budget', 'to_budget', 'amount', 'transfer_date', 'approved')
    list_filter = ('approved', 'transfer_date')
    search_fields = ('reason',)
    date_hierarchy = 'transfer_date'
    raw_id_fields = ('from_budget', 'to_budget', 'approved_by')
