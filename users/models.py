from django.db import models
from django.contrib.auth.models import User

# User model
''' 
    "Feature/user-model" branch is focused on user foundation and relationships

    # Optional: we might extend the User model later with a Profile if needed (Setting up custom authentication + Adding signals (like auto profile creation))
    # For now, we'll just add a placeholder for future relationships
    # No extra fields, to keep the app focused on achievements  
'''


# Certificate model
class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255)
    date_earned = models.DateField()
    file_upload = models.FileField(upload_to="certificates/", blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.issuer}"


# Project model
class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    certificate = models.ForeignKey(Certificate, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# Goal model
class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    target_projects = models.IntegerField()
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.target_projects} projects by {self.deadline}"
