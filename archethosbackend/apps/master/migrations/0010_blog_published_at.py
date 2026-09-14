from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("master", "0009_blog_excerpt_slug")]

    operations = [
        migrations.AddField(
            model_name="blog",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
