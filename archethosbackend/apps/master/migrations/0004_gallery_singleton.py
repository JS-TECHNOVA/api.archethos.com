from django.db import migrations, models


def create_gallery(apps, schema_editor):
    apps.get_model("master", "Gallery").objects.get_or_create(pk=1)


class Migration(migrations.Migration):

    dependencies = [("master", "0003_gallery_galleryitem")]

    operations = [
        migrations.RunPython(create_gallery, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="gallery",
            constraint=models.CheckConstraint(condition=models.Q(pk=1), name="gallery_singleton"),
        ),
    ]
