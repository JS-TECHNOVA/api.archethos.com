import django.db.models.deletion
from django.db import migrations, models


def create_blogs_page(apps, schema_editor):
    apps.get_model("blogs", "BlogsPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):

    dependencies = [("blogs", "0001_move_from_master")]

    operations = [
        migrations.CreateModel(
            name="BlogsPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hero_title", models.CharField(blank=True, max_length=255)),
                ("hero_description", models.TextField(blank=True)),
                ("meta_title", models.CharField(blank=True, max_length=255)),
                ("meta_description", models.TextField(blank=True)),
                ("meta_keywords", models.CharField(blank=True, max_length=255)),
                ("featured_blogs", models.ManyToManyField(blank=True, related_name="featured_on_blogs_pages", to="blogs.blog")),
                ("hero_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blogs_page_hero_images", to="media_library.mediaasset")),
            ],
        ),
        migrations.RunPython(create_blogs_page, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="blogspage",
            constraint=models.CheckConstraint(condition=models.Q(pk=1), name="blogs_page_singleton"),
        ),
    ]
