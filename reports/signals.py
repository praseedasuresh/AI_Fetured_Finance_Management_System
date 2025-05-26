from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import ScheduledReport, SavedReport
from django.utils import timezone
import os

# This file is intentionally created to handle signals for the reports app.
# It's referenced in ReportsConfig.ready() method.

@receiver(post_save, sender=ScheduledReport)
def update_next_run_date(sender, instance, created, **kwargs):
    """
    Update the next run date for a scheduled report when it's created or modified
    """
    if created and not instance.next_run:
        # Set initial next_run date based on frequency if not provided
        instance.calculate_next_run()
        instance.save(update_fields=['next_run'])

@receiver(pre_delete, sender=SavedReport)
def delete_report_file(sender, instance, **kwargs):
    """
    Delete the file associated with a saved report when the report is deleted
    """
    if instance.file and os.path.isfile(instance.file.path):
        try:
            os.remove(instance.file.path)
        except (OSError, FileNotFoundError):
            # Log but don't raise exception if file deletion fails
            pass
