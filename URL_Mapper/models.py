from django.db import models
import datetime
from django.utils import timezone
# Create your models here.
class URL(models.Model):
    Long_url=models.URLField(unique=True) # This will store the original url
    Short_url=models.CharField(max_length=200, unique=True) # This will store the shorten url

    def __str__(self):
        return self.Long_url