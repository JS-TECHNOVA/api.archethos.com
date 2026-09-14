from django.db import migrations


MAKE_LEGACY_COLUMNS_NULLABLE = """
DO $$
DECLARE
    legacy_column text;
BEGIN
    FOREACH legacy_column IN ARRAY ARRAY[
        'media_type', 'source_type', 'external_url', 'external_id',
        'thumbnail_url', 'file_name', 'mime_type', 'checksum', 'caption',
        'description', 'tags', 'media_location'
    ]
    LOOP
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'media_library_mediaasset'
              AND column_name = legacy_column
        ) THEN
            EXECUTE format(
                'ALTER TABLE media_library_mediaasset ALTER COLUMN %I DROP NOT NULL',
                legacy_column
            );
        END IF;
    END LOOP;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [("media_library", "0002_legacy_updated_at_default")]

    operations = [migrations.RunSQL(MAKE_LEGACY_COLUMNS_NULLABLE, migrations.RunSQL.noop)]
