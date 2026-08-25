from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from clubs.models import ClubMembership
from locations.models import Location


@receiver(pre_save, sender=ClubMembership)
def _stash_previous_is_active(sender, instance, **kwargs):
    """Record is_active before save, so post_save can detect a True->False flip."""
    if not instance.pk:
        instance._previous_is_active = None
        return
    try:
        instance._previous_is_active = (
            ClubMembership.objects.only("is_active").get(pk=instance.pk).is_active
        )
    except ClubMembership.DoesNotExist:
        instance._previous_is_active = None


@receiver(post_save, sender=ClubMembership)
def redact_locations_on_membership_deactivate(sender, instance, created, **kwargs):
    if created:
        return
    if getattr(instance, "_previous_is_active", None) and not instance.is_active:
        Location.redact_for_departed_member(instance.user, instance.club)


@receiver(post_delete, sender=ClubMembership)
def redact_locations_on_membership_delete(sender, instance, **kwargs):
    Location.redact_for_departed_member(instance.user, instance.club)
