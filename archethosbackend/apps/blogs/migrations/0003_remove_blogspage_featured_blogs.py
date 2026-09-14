from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("blogs", "0002_blogspage")]

    operations = [
        migrations.RemoveField(model_name="blogspage", name="featured_blogs"),
    ]
