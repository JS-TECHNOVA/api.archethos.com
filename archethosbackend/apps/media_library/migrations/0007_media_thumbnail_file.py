from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("media_library", "0006_tags_json")]

    operations = [
        migrations.AddField(
            model_name="mediaasset",
            name="thumbnail_file",
            field=models.FileField(blank=True, null=True, upload_to="media/thumbnails/"),
        ),
    ]
