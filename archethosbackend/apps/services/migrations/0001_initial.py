import django.db.models.deletion
from django.db import migrations, models


def create_services_page(apps, schema_editor):
    apps.get_model("services", "ServicesPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="Service", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("number", models.CharField(blank=True, max_length=10)), ("order", models.PositiveIntegerField(default=0)),
            ("title", models.CharField(max_length=200)), ("title_lines", models.JSONField(blank=True, default=list)),
            ("slug", models.SlugField(blank=True, max_length=220, unique=True)), ("is_featured", models.BooleanField(default=False)),
            ("is_visible", models.BooleanField(default=True)), ("hero_heading", models.CharField(blank=True, max_length=255)),
            ("short_description", models.TextField(blank=True)), ("description", models.TextField(blank=True)),
            ("sections", models.JSONField(blank=True, default=list)), ("process_eyebrow", models.CharField(blank=True, max_length=255)),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)),
            ("meta_keywords", models.CharField(blank=True, max_length=255)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("hero_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_hero_images", to="media_library.mediaasset")),
            ("index_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_index_images", to="media_library.mediaasset")),
            ("gallery", models.ManyToManyField(blank=True, related_name="service_galleries", to="media_library.mediaasset")),
        ], options={"ordering": ["order", "title"]}),
        migrations.CreateModel(name="ServicesPage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("hero_eyebrow", models.CharField(blank=True, max_length=255)), ("hero_title", models.CharField(blank=True, max_length=255)),
            ("hero_description", models.TextField(blank=True)), ("meta_title", models.CharField(blank=True, max_length=255)),
            ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("hero_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="services_page_hero_images", to="media_library.mediaasset")),
        ]),
        migrations.CreateModel(name="ServicesWorkProcess", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("number", models.CharField(blank=True, max_length=10)), ("title", models.CharField(max_length=255)),
            ("description", models.TextField(blank=True)), ("order", models.PositiveIntegerField(default=0)),
            ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_processes", to="services.service")),
        ], options={"ordering": ["order", "id"]}),
        migrations.RunPython(create_services_page, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="servicespage", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="services_page_singleton")),
    ]
