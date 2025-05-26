from django.db import models
from users.models import User
from core.models import TimeStampedModel


class ChatSession(TimeStampedModel):
    """Model for storing chat sessions between users and the AI assistant"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Chat with {self.user.get_full_name()} ({self.created_at.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-created_at']


class ChatMessage(TimeStampedModel):
    """Model for storing individual messages in a chat session"""
    MESSAGE_TYPES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    def __str__(self):
        return f"{self.message_type.capitalize()} message in {self.session}"
    
    class Meta:
        ordering = ['created_at']


class FinancialQuery(TimeStampedModel):
    """Model for storing financial queries and their results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_queries')
    query_text = models.TextField()
    result_summary = models.TextField(blank=True, null=True)
    parameters = models.JSONField(default=dict, blank=True)
    execution_time = models.FloatField(default=0.0)  # Time taken to process the query in seconds
    
    def __str__(self):
        return f"Query by {self.user.get_full_name()}: {self.query_text[:50]}..."
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Financial queries"


class ExpenseAnomaly(TimeStampedModel):
    """Model for storing detected expense anomalies"""
    expense = models.ForeignKey('expenses.Expense', on_delete=models.CASCADE, related_name='anomalies')
    anomaly_type = models.CharField(max_length=50, choices=(
        ('amount', 'Unusual Amount'),
        ('frequency', 'Unusual Frequency'),
        ('category', 'Category Mismatch'),
        ('department', 'Department Anomaly'),
        ('other', 'Other Anomaly')
    ))
    confidence_score = models.FloatField(help_text="Confidence score (0-1) of the anomaly detection")
    description = models.TextField(help_text="Description of why this expense was flagged as anomalous")
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_anomalies')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_false_positive = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Anomaly in {self.expense} ({self.anomaly_type})"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Expense anomalies"
