from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, StudentProfile


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create a student profile when a student user is created"""
    if created and instance.is_student:
        StudentProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """Save the student profile when the user is saved"""
    if instance.is_student:
        try:
            instance.student_profile.save()
        except StudentProfile.DoesNotExist:
            # Create the profile if it doesn't exist
            StudentProfile.objects.create(user=instance)
