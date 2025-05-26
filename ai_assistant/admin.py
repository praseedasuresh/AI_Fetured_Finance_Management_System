from django.contrib import admin
from .models import ChatSession, ChatMessage, FinancialQuery


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Admin configuration for ChatSession model"""
    list_display = ('id', 'user', 'title', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'user__email', 'user__first_name', 'user__last_name')
    date_hierarchy = 'created_at'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin configuration for ChatMessage model"""
    list_display = ('id', 'session', 'message_type', 'short_content', 'created_at')
    list_filter = ('message_type', 'created_at')
    search_fields = ('content', 'session__title', 'session__user__email')
    date_hierarchy = 'created_at'
    
    def short_content(self, obj):
        """Return a truncated version of the message content"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    
    short_content.short_description = 'Content'


@admin.register(FinancialQuery)
class FinancialQueryAdmin(admin.ModelAdmin):
    """Admin configuration for FinancialQuery model"""
    list_display = ('id', 'user', 'short_query', 'execution_time', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query_text', 'result_summary', 'user__email')
    date_hierarchy = 'created_at'
    
    def short_query(self, obj):
        """Return a truncated version of the query text"""
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    
    short_query.short_description = 'Query'
