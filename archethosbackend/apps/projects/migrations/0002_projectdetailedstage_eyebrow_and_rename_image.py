from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="projectdetailedstage",
            name="eyebrow",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RenameField(
            model_name="projectdetailedstage",
            old_name="image",
            new_name="media",
        ),
        migrations.AlterField(
            model_name="projectdetailedstage",
            name="media",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="project_stage_media", to="media_library.mediaasset"),
        ),
    ]
