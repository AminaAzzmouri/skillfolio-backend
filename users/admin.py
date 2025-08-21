from django.contrib import admin
from .models import Certificate, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "certificate", "date_created")
    
admin.site.register(Certificate)