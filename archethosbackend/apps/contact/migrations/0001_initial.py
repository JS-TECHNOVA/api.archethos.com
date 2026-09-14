import django.db.models.deletion
from django.db import migrations, models


def create_contact_page(apps, schema_editor):
    apps.get_model("contact", "ContactPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [("home", "0004_homecontentgroup"), ("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.CreateModel(name="ContactPage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("form_eyebrow", models.CharField(blank=True, max_length=255)), ("next_eyebrow", models.CharField(blank=True, max_length=255)),
            ("next_title", models.CharField(blank=True, max_length=255)), ("next_steps", models.JSONField(blank=True, default=list)),
            ("meta_title", models.CharField(blank=True, max_length=255)), ("meta_description", models.TextField(blank=True)), ("meta_keywords", models.CharField(blank=True, max_length=255)),
            ("sidebar_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contact_sidebar_images", to="media_library.mediaasset")),
            ("slider", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contact_pages", to="home.slider")),
        ]),
        migrations.RunPython(create_contact_page, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="contactpage", constraint=models.CheckConstraint(condition=models.Q(pk=1), name="contact_page_singleton")),
    ]
