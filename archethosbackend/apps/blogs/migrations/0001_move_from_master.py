import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("media_library", "0007_media_thumbnail_file"),
        ("master", "0010_blog_published_at"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="BlogCategory",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=100, unique=True)),
                        ("description", models.TextField(blank=True)),
                    ],
                    options={"db_table": "master_blogcategory"},
                ),
                migrations.CreateModel(
                    name="Blog",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=200)),
                        ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
                        ("excerpt", models.TextField(blank=True)),
                        ("content", models.TextField()),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("published_at", models.DateTimeField(blank=True, null=True)),
                        ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")], default="draft", max_length=10)),
                        ("tags", models.CharField(blank=True, max_length=255)),
                        ("view_count", models.PositiveIntegerField(default=0)),
                        ("meta_title", models.CharField(blank=True, max_length=255)),
                        ("meta_description", models.TextField(blank=True)),
                        ("meta_keywords", models.CharField(blank=True, max_length=255)),
                        ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blogs", to=settings.AUTH_USER_MODEL)),
                        ("featured_image", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="featured_blogs", to="media_library.mediaasset")),
                        ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blogs", to="blogs.blogcategory")),
                    ],
                    options={"db_table": "master_blog", "ordering": ["-created_at"]},
                ),
                migrations.CreateModel(
                    name="BlogComment",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("content", models.TextField()),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blog_comments", to=settings.AUTH_USER_MODEL)),
                        ("blog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="blogs.blog")),
                    ],
                    options={"db_table": "master_blogcomment", "ordering": ["-created_at"]},
                ),
            ],
        ),
    ]
