from django.db import migrations, models


ADD_MEDIA_SOURCE_COLUMNS = """
ALTER TABLE media_library_mediaasset ALTER COLUMN file DROP NOT NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS media_type varchar(20) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS source_type varchar(20) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS external_url varchar(500) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS external_id varchar(255) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS thumbnail_url varchar(500) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS file_name varchar(255) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS mime_type varchar(255) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS caption varchar(500) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS description text NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS tags varchar(500) NULL;
ALTER TABLE media_library_mediaasset ADD COLUMN IF NOT EXISTS media_location varchar(255) NULL;
"""


class Migration(migrations.Migration):

    dependencies = [("media_library", "0003_legacy_columns_nullable")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(ADD_MEDIA_SOURCE_COLUMNS, migrations.RunSQL.noop)],
            state_operations=[
                migrations.AlterField(
                    model_name="mediaasset",
                    name="file",
                    field=models.FileField(blank=True, null=True, upload_to="media/"),
                ),
                migrations.AddField(model_name="mediaasset", name="media_type", field=models.CharField(blank=True, max_length=20)),
                migrations.AddField(model_name="mediaasset", name="source_type", field=models.CharField(blank=True, max_length=20)),
                migrations.AddField(model_name="mediaasset", name="external_url", field=models.URLField(blank=True, max_length=500)),
                migrations.AddField(model_name="mediaasset", name="external_id", field=models.CharField(blank=True, max_length=255)),
                migrations.AddField(model_name="mediaasset", name="thumbnail_url", field=models.URLField(blank=True, max_length=500)),
                migrations.AddField(model_name="mediaasset", name="file_name", field=models.CharField(blank=True, max_length=255)),
                migrations.AddField(model_name="mediaasset", name="mime_type", field=models.CharField(blank=True, max_length=255)),
                migrations.AddField(model_name="mediaasset", name="caption", field=models.CharField(blank=True, max_length=500)),
                migrations.AddField(model_name="mediaasset", name="description", field=models.TextField(blank=True)),
                migrations.AddField(model_name="mediaasset", name="tags", field=models.CharField(blank=True, max_length=500)),
                migrations.AddField(model_name="mediaasset", name="media_location", field=models.CharField(blank=True, max_length=255)),
            ],
        ),
    ]
