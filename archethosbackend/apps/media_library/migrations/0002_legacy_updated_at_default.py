from django.db import migrations


SET_LEGACY_UPDATED_AT_DEFAULT = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'media_library_mediaasset'
          AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE media_library_mediaasset
        ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [("media_library", "0001_initial")]

    operations = [migrations.RunSQL(SET_LEGACY_UPDATED_AT_DEFAULT, migrations.RunSQL.noop)]
