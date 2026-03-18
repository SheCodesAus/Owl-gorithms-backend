from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

class BucketlistsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bucketlists"
    
    def ready(self):
        import bucketlists.signals