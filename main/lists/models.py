from django.db import models
from users.models import User

# Create your models here.
class List(models.Model):
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.URLField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=50,
        choices=[
            ('one', 'One'),
            ('two', 'Two'),
            ('three', 'Three'),
        ])
    
    has_deadline = models.BooleanField(default=False)
    deadline = models.DateTimeField(null=True, blank=True)
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_lists'
    )
    
    contributor = models.ManyToManyField(
        User,
        blank=True,
        related_name='contributor_lists'
    )
    
    def __str__(self):
        return f"{self.title}"