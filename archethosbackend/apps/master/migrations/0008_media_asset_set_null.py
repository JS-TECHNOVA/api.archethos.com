import django.db.models.deletion
from django.db import migrations, models


def make_media_asset_references_nullable(apps, schema_editor):
    connection = schema_editor.connection
    target = ("media_library_mediaasset", "id")
    quote = schema_editor.quote_name

    with connection.cursor() as cursor:
        for table_name in connection.introspection.table_names(cursor):
            constraints = connection.introspection.get_constraints(cursor, table_name)
            for constraint_name, details in constraints.items():
                if details.get("foreign_key") != target:
                    continue

                column_name = details["columns"][0]
                cursor.execute(
                    f"ALTER TABLE {quote(table_name)} ALTER COLUMN {quote(column_name)} DROP NOT NULL"
                )
                cursor.execute(
                    f"ALTER TABLE {quote(table_name)} DROP CONSTRAINT {quote(constraint_name)}"
                )
                cursor.execute(
                    f"ALTER TABLE {quote(table_name)} "
                    f"ADD CONSTRAINT {quote(constraint_name)} "
                    f"FOREIGN KEY ({quote(column_name)}) "
                    f"REFERENCES {quote(target[0])} ({quote(target[1])}) ON DELETE SET NULL"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("media_library", "0005_media_location_nullable"),
        ("master", "0007_gallery_hero_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="galleryitem",
            name="asset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gallery_items",
                to="media_library.mediaasset",
            ),
        ),
        migrations.RunPython(make_media_asset_references_nullable, migrations.RunPython.noop),
    ]
