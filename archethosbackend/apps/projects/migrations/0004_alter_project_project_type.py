from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0003_project_project_type")]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="project_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("architecture", "Architecture Design"),
                    ("interior", "Interior Design"),
                    ("exterior", "Exterior Design"),
                    ("vastu", "Vastu Consultancy"),
                    ("construction", "Construction"),
                    ("renovation", "Renovation"),
                ],
                max_length=20,
            ),
        ),
    ]
