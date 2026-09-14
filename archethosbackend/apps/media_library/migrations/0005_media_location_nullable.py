from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("media_library", "0004_media_asset_sources")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="mediaasset",
                    name="media_location",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
        ),
    ]
