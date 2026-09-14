from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("blogs", "0001_move_from_master"), ("master", "0010_blog_published_at")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="BlogComment"),
                migrations.DeleteModel(name="Blog"),
                migrations.DeleteModel(name="BlogCategory"),
            ],
        ),
    ]
