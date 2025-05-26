from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import ReportTemplate, SavedReport, ScheduledReport


@admin.register(ReportTemplate)
class ReportTemplateAdmin(ImportExportModelAdmin):
    """Admin interface for ReportTemplate model"""
    list_display = ('title', 'report_type', 'is_system', 'created_by', 'created_at')
    list_filter = ('report_type', 'is_system', 'created_at')
    search_fields = ('title', 'description', 'created_by__username', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'report_type', 'is_system')
        }),
        ('Template Configuration', {
            'fields': ('template_data',)
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(SavedReport)
class SavedReportAdmin(ImportExportModelAdmin):
    """Admin interface for SavedReport model"""
    list_display = ('title', 'template', 'academic_year', 'department', 'created_by', 'created_at')
    list_filter = ('academic_year', 'department', 'template__report_type', 'created_at')
    search_fields = ('title', 'description', 'created_by__username', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'template', 'academic_year', 'department')
        }),
        ('Report Data', {
            'fields': ('report_data', 'parameters', 'file')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(ScheduledReport)
class ScheduledReportAdmin(ImportExportModelAdmin):
    """Admin interface for ScheduledReport model"""
    list_display = ('title', 'template', 'frequency', 'next_run', 'is_active', 'created_by')
    list_filter = ('frequency', 'is_active', 'next_run', 'created_at')
    search_fields = ('title', 'description', 'created_by__username', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('recipients',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'template')
        }),
        ('Schedule Configuration', {
            'fields': ('frequency', 'next_run', 'is_active', 'parameters')
        }),
        ('Recipients', {
            'fields': ('recipients',)
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
