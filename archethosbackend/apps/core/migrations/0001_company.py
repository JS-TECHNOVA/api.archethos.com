import django.db.models.deletion
from django.db import migrations, models


def create_company(apps, schema_editor):
    apps.get_model("core", "Company").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="Company", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(blank=True, max_length=255)), ("tagline", models.CharField(blank=True, max_length=500)),
            ("gst", models.CharField(blank=True, max_length=50)), ("address", models.TextField(blank=True)),
            ("header_links", models.JSONField(blank=True, default=list)), ("footer_links", models.JSONField(blank=True, default=list)),
            ("locations", models.JSONField(blank=True, default=list)), ("contacts", models.JSONField(blank=True, default=list)),
            ("socials", models.JSONField(blank=True, default=list)), ("meta_title", models.CharField(blank=True, max_length=255)),
            ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("head_inject_code", models.TextField(blank=True)), ("body_inject_code", models.TextField(blank=True)),
            ("icon", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="company_icons", to="media_library.mediaasset")),
            ("logo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="company_logos", to="media_library.mediaasset")),
        ]),
        migrations.RunPython(create_company, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="company", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="company_singleton")),
    ]
