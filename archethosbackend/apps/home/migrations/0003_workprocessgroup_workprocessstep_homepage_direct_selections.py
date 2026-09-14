import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0002_counter_homecountersgroup"),
        ("master", "0011_move_blogs_to_blogs_app"),
        ("projects", "0004_alter_project_project_type"),
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(name="WorkProcessGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)),
            ("description", models.TextField(blank=True)), ("is_visible", models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name="WorkProcessStep", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("number", models.CharField(blank=True, max_length=10)), ("title", models.CharField(max_length=255)),
            ("description", models.TextField(blank=True)), ("order", models.PositiveIntegerField(default=0)),
            ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="home.workprocessgroup")),
        ], options={"ordering": ["order", "id"]}),
        migrations.AddField(model_name="homepage", name="featured_project", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="featured_on_home_pages", to="projects.project")),
        migrations.AddField(model_name="homepage", name="featured_service", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="featured_on_home_pages", to="services.service")),
        migrations.AddField(model_name="homepage", name="selected_gallery_items", field=models.ManyToManyField(blank=True, related_name="selected_on_home_pages", to="master.galleryitem")),
        migrations.AddField(model_name="homepage", name="work_process_group", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="home_pages", to="home.workprocessgroup")),
    ]
