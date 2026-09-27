from django.contrib import admin

from .models import Blog, BlogCategory, BlogComment, BlogsPage


admin.site.register([BlogCategory, Blog, BlogComment, BlogsPage])
