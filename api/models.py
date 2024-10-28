from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class InviteCode(models.Model):
    code = models.CharField(max_length=255, unique=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Set the expires_at field to be 24 hours after the created_at timestamp
    expires_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())  # Generate a unique code if not provided
        # Set expires_at only when the instance is created
        if not self.pk:  # Only set this if the instance is being created
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at


class UserProfile(models.Model):
    username = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=128)  # Store hashed password in production
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('developer', 'Developer'),
    ]
    role = models.CharField(max_length=255, choices=ROLE_CHOICES, default='viewer')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class Cluster(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(UserProfile, related_name='user_clusters', on_delete=models.CASCADE)

    # Total resources available in the cluster
    total_cpu = models.FloatField()  # Total CPU available (in cores)
    total_gpu = models.FloatField()   # Total GPUs available
    total_ram = models.FloatField()   # Total RAM available (in GB)

    # Resources currently utilized
    utilized_cpu = models.FloatField(default=0)    # CPU currently being utilized
    utilized_gpu = models.FloatField(default=0)     # GPUs currently being utilized
    utilized_ram = models.FloatField(default=0)     # RAM currently being utilized

    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class Deployment(models.Model):
    name = models.CharField(max_length=255, default="deployment")
    docker_image = models.CharField(max_length=255)
    ram_required = models.FloatField()
    cpu_required = models.FloatField()
    gpu_required = models.FloatField()
    cluster = models.ForeignKey(Cluster, related_name='deployments', on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(UserProfile, related_name='user_deployments', on_delete=models.CASCADE)
    
    status = models.CharField(max_length=50, default='queued')
    priority = models.CharField(max_length=10, choices=[('high', 'High'), ('low', 'Low')])

    def __str__(self):
        return f"{self.docker_image} - {self.status} ({self.priority})"
