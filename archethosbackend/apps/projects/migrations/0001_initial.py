import django.db.models.deletion
from django.db import migrations, models


def create_project_page(apps, schema_editor):
    apps.get_model("projects", "ProjectPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="ProjectCategory", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100, unique=True)), ("description", models.TextField(blank=True)),
            ("order", models.PositiveIntegerField(default=0)),
        ], options={"ordering": ["order", "name"]}),
        migrations.CreateModel(name="Project", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=200)), ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
            ("location", models.CharField(blank=True, max_length=255)), ("year", models.PositiveIntegerField(blank=True, null=True)),
            ("project_status", models.CharField(blank=True, max_length=100)), ("services", models.JSONField(blank=True, default=list)),
            ("short_description", models.TextField(blank=True)), ("description", models.TextField(blank=True)),
            ("layout", models.CharField(blank=True, max_length=20)), ("is_featured", models.BooleanField(default=False)),
            ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")], default="draft", max_length=10)),
            ("published_at", models.DateTimeField(blank=True, null=True)), ("meta_title", models.CharField(blank=True, max_length=255)),
            ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects", to="projects.projectcategory")),
            ("cover_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_covers", to="media_library.mediaasset")),
        ], options={"ordering": ["-published_at", "-created_at"]}),
        migrations.CreateModel(name="ProjectPage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("hero_title", models.CharField(blank=True, max_length=255)), ("hero_description", models.TextField(blank=True)),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("hero_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects_page_hero_images", to="media_library.mediaasset")),
        ]),
        migrations.CreateModel(name="ProjectGallery", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(blank=True, max_length=255)), ("caption", models.TextField(blank=True)), ("description", models.TextField(blank=True)), ("order", models.PositiveIntegerField(default=0)),
            ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_gallery_items", to="media_library.mediaasset")),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gallery", to="projects.project")),
        ], options={"ordering": ["order", "id"]}),
        migrations.CreateModel(name="ProjectDetailedStage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=255)), ("description", models.TextField()), ("order", models.PositiveIntegerField(default=0)),
            ("image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_stage_images", to="media_library.mediaasset")),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detailed_stages", to="projects.project")),
        ], options={"ordering": ["order", "id"]}),
        migrations.RunPython(create_project_page, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="projectpage", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="projects_page_singleton")),
    ]
