import django.db.models.deletion
from django.db import migrations, models


def create_home_page(apps, schema_editor):
    apps.get_model("home", "HomePage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("media_library", "0007_media_thumbnail_file"),
        ("master", "0011_move_blogs_to_blogs_app"),
        ("projects", "0004_alter_project_project_type"),
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(name="Slider", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("label", models.CharField(blank=True, max_length=100)), ("eyebrow", models.CharField(blank=True, max_length=255)),
            ("title", models.CharField(max_length=255)), ("description", models.TextField(blank=True)),
            ("primary_cta_label", models.CharField(blank=True, max_length=100)), ("primary_cta_url", models.CharField(blank=True, max_length=255)),
            ("secondary_cta_label", models.CharField(blank=True, max_length=100)), ("secondary_cta_url", models.CharField(blank=True, max_length=255)),
            ("order", models.PositiveIntegerField(default=0)), ("is_visible", models.BooleanField(default=True)),
            ("media", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sliders", to="media_library.mediaasset")),
        ], options={"ordering": ["order", "id"]}),
        migrations.CreateModel(name="HomePage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("sliders", models.ManyToManyField(blank=True, related_name="home_pages", to="home.slider")),
        ]),
        migrations.CreateModel(name="HomeServicesGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)), ("description", models.TextField(blank=True)),
            ("page", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="services_group", to="home.homepage")),
            ("services", models.ManyToManyField(blank=True, related_name="home_service_groups", to="services.service")),
        ]),
        migrations.CreateModel(name="HomeProjectsGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)), ("description", models.TextField(blank=True)),
            ("page", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="projects_group", to="home.homepage")),
            ("projects", models.ManyToManyField(blank=True, related_name="home_project_groups", to="projects.project")),
        ]),
        migrations.CreateModel(name="HomeGalleryGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)), ("description", models.TextField(blank=True)),
            ("gallery_items", models.ManyToManyField(blank=True, related_name="home_gallery_groups", to="master.galleryitem")),
            ("page", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="gallery_group", to="home.homepage")),
        ]),
        migrations.RunPython(create_home_page, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="homepage", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="home_page_singleton")),
    ]
