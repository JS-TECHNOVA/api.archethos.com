from django.contrib import admin

from .models import FAQ, Gallery, GalleryCategory, GalleryItem


admin.site.register([FAQ, Gallery, GalleryCategory, GalleryItem])
