from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0003_servicespage_how_project_moves"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="tagline",
            field=models.TextField(blank=True),
        ),
    ]
