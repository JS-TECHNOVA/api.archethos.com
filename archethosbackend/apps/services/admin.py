from django.contrib import admin

from .models import Service, ServiceWorkStage, ServicesGallery, ServicesPage


admin.site.register([Service, ServiceWorkStage, ServicesGallery, ServicesPage])
