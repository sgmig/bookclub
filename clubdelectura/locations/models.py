from django.conf import settings
from django.db import models

# Create your models here.


# TODO: Add coordinates
class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )
    is_private = models.BooleanField(
        default=True,
        blank=True,
        help_text=(
            "Private locations (e.g. a member's home) have their address and "
            "access details redacted once the creator leaves the club."
        ),
    )

    def __str__(self):
        return self.name

    @classmethod
    def redact_for_departed_member(cls, user, club):
        """Clear sensitive fields on private locations `user` created for `club`.

        Called when their membership in that club ends. Keeps `name` so
        past meetings still show where they were held, without exposing
        how to get there to anyone who joins later.
        """
        cls.objects.filter(
            created_by=user, is_private=True, club_locations__club=club
        ).update(address="", access_details="", description="")
