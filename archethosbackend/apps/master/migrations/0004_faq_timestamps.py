from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [("master", "0003_gallery_galleryitem")]

    operations = [
        migrations.AddField(
            model_name="faq",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="faq",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
    ]
