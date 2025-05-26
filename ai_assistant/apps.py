from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_assistant'
    verbose_name = 'AI Finance Assistant'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import any signals here if needed
        pass
