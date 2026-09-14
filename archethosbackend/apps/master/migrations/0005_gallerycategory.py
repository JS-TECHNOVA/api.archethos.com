from django.db import migrations, models
import django.db.models.deletion


def assign_uncategorized_category(apps, schema_editor):
    GalleryCategory = apps.get_model("master", "GalleryCategory")
    GalleryItem = apps.get_model("master", "GalleryItem")
    category, _ = GalleryCategory.objects.get_or_create(gallery_id=1, name="Uncategorized")
    GalleryItem.objects.filter(category__isnull=True).update(category_id=category.pk)


class Migration(migrations.Migration):

    dependencies = [("master", "0004_gallery_singleton")]

    operations = [
        migrations.CreateModel(
            name="GalleryCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                ("gallery", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="categories", to="master.gallery")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="gallerycategory",
            constraint=models.UniqueConstraint(fields=("gallery", "name"), name="unique_gallery_category_name"),
        ),
        migrations.AddField(
            model_name="galleryitem",
            name="category",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="items", to="master.gallerycategory"),
        ),
        migrations.RunPython(assign_uncategorized_category, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="galleryitem",
            name="category",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="master.gallerycategory"),
        ),
        migrations.RemoveConstraint(model_name="galleryitem", name="unique_gallery_asset"),
        migrations.RemoveField(model_name="galleryitem", name="gallery"),
        migrations.AddConstraint(
            model_name="galleryitem",
            constraint=models.UniqueConstraint(fields=("asset",), name="unique_gallery_asset"),
        ),
    ]
