from django.db import migrations, models


CONVERT_TAGS_TO_JSON = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'media_library_mediaasset'
          AND column_name = 'tags'
          AND udt_name <> 'jsonb'
    ) THEN
        ALTER TABLE media_library_mediaasset
        ALTER COLUMN tags TYPE jsonb
        USING CASE
            WHEN tags IS NULL OR btrim(tags) = '' THEN '[]'::jsonb
            ELSE to_jsonb(regexp_split_to_array(tags, '\\s*,\\s*'))
        END;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [("media_library", "0005_media_location_nullable")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(CONVERT_TAGS_TO_JSON, migrations.RunSQL.noop)],
            state_operations=[
                migrations.AlterField(
                    model_name="mediaasset",
                    name="tags",
                    field=models.JSONField(blank=True, null=True),
                ),
            ],
        ),
    ]
