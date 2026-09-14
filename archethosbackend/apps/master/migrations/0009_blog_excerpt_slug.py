from django.db import migrations, models
from django.utils.text import slugify


def populate_blog_slugs(apps, schema_editor):
    Blog = apps.get_model("master", "Blog")
    for blog in Blog.objects.filter(slug__isnull=True).order_by("id"):
        base = slugify(blog.title) or f"blog-{blog.pk}"
        slug = base[:220]
        number = 2
        while Blog.objects.filter(slug=slug).exclude(pk=blog.pk).exists():
            suffix = f"-{number}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
            number += 1
        blog.slug = slug
        blog.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [("master", "0008_media_asset_set_null")]

    operations = [
        migrations.AddField(
            model_name="blog",
            name="excerpt",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="blog",
            name="slug",
            field=models.SlugField(blank=True, max_length=220, null=True, unique=True),
        ),
        migrations.RunPython(populate_blog_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="blog",
            name="slug",
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]
