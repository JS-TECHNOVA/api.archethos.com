import django.db.models.deletion
from django.db import migrations, models


def move_hero_image_to_media_library(apps, schema_editor):
    AboutPage = apps.get_model("about", "AboutPage")
    MediaAsset = apps.get_model("media_library", "MediaAsset")
    for page in AboutPage.objects.exclude(hero_image=""):
        asset, _ = MediaAsset.objects.get_or_create(
            external_url=page.hero_image,
            defaults={"media_type": "image", "source_type": "EXTERNAL", "title": "About hero"},
        )
        page.hero_media_id = asset.id
        page.save(update_fields=["hero_media"])


class Migration(migrations.Migration):
    dependencies = [("about", "0005_remove_aboutpage_mission_remove_aboutpage_vision")]

    operations = [
        migrations.AddField(model_name="aboutpage", name="hero_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="hero_media", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_hero_media", to="media_library.mediaasset")),
        migrations.RunPython(move_hero_image_to_media_library, migrations.RunPython.noop),
        migrations.RemoveField(model_name="aboutpage", name="hero_image"),
    ]
