from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Trainer, TrainerProfile

@receiver(post_save, sender=Trainer)
def create_trainer_profile(sender, instance, created, **kwargs):
    if created:
        TrainerProfile.objects.create(trainer=instance)





