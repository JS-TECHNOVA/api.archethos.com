import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="Page", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=255)), ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
            ("is_active", models.BooleanField(default=False)), ("hero_eyebrow", models.CharField(blank=True, max_length=255)),
            ("hero_title", models.CharField(blank=True, max_length=255)), ("hero_description", models.TextField(blank=True)),
            ("content_heading", models.CharField(blank=True, max_length=255)), ("body", models.JSONField(blank=True, default=dict)),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)),
            ("meta_keywords", models.CharField(blank=True, max_length=255)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("hero_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="custom_page_hero_images", to="media_library.mediaasset")),
        ], options={"ordering": ["title"]}),
    ]
