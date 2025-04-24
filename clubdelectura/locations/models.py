from django.db import models

# Create your models here.


# TODO: Add coordinates
class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
