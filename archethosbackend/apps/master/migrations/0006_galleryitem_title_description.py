from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("master", "0005_gallerycategory")]

    operations = [
        migrations.AddField(
            model_name="galleryitem",
            name="title",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="galleryitem",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]
