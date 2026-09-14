import django.db.models.deletion
from django.db import migrations, models


def create_about_page(apps, schema_editor):
    apps.get_model("about", "AboutPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [("home", "0001_initial"), ("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="AboutPage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("slider", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_pages", to="home.slider")),
        ]),
        migrations.CreateModel(name="AboutGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("group_type", models.CharField(choices=[("studio_story", "Studio story"), ("mission_vision", "Mission and vision"), ("founder_message", "Founder message"), ("approach", "Approach"), ("philosophy", "Philosophy"), ("presence", "Presence"), ("cta", "CTA")], max_length=30)),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)), ("description", models.TextField(blank=True)), ("content", models.JSONField(blank=True, default=dict)), ("order", models.PositiveIntegerField(default=0)),
            ("media", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_groups", to="media_library.mediaasset")),
            ("page", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="groups", to="about.aboutpage")),
        ], options={"ordering": ["order", "id"]}),
        migrations.RunPython(create_about_page, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="aboutpage", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="about_page_singleton")),
        migrations.AddConstraint(model_name="aboutgroup", constraint=models.UniqueConstraint(fields=("page", "group_type"), name="about_page_group_type_unique")),
    ]
