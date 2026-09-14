from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0002_projectdetailedstage_eyebrow_and_rename_image")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="project_type",
            field=models.CharField(blank=True, choices=[("interior", "Interior"), ("exterior", "Exterior"), ("renovation", "Renovation")], max_length=20),
        ),
    ]
