from django.contrib import admin
from .models import Certificate, Project, Goal


admin.site.register(Certificate)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "certificate", "date_created")

admin.site.register(Goal)
