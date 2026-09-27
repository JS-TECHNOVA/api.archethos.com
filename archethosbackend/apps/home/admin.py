from django.contrib import admin

from .models import HomePage, Slider


admin.site.register([Slider, HomePage])
