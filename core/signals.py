from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# This file is intentionally created to handle signals for the core app.
# Currently, it's empty but referenced in CoreConfig.ready() method.
# You can add signal handlers here as needed for the core models.

# Example of a signal handler:
# @receiver(post_save, sender=YourModel)
# def handle_model_save(sender, instance, created, **kwargs):
#     """
#     Handle actions after a model is saved
#     """
#     if created:
#         # Do something when a new instance is created
#         pass
#     else:
#         # Do something when an existing instance is updated
#         pass
