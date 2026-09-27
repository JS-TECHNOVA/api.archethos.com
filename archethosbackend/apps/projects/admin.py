from django.contrib import admin

from .models import Project, ProjectCategory, ProjectDetailedStage, ProjectGallery, ProjectPage


admin.site.register([ProjectCategory, Project, ProjectGallery, ProjectDetailedStage, ProjectPage])
