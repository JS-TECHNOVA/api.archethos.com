from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_company")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="whatsapp_link",
            field=models.URLField(blank=True),
        ),
        migrations.CreateModel(name="Enquiry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=255)), ("email", models.EmailField(max_length=254)),
            ("phone", models.CharField(blank=True, max_length=50)), ("project_type", models.CharField(max_length=100)),
            ("location", models.CharField(max_length=255)), ("scope", models.CharField(blank=True, max_length=255)),
            ("source", models.CharField(blank=True, max_length=100)), ("services", models.JSONField(blank=True, default=list)),
            ("message", models.TextField()),
            ("status", models.CharField(choices=[("new", "New"), ("in_progress", "In progress"), ("responded", "Responded"), ("closed", "Closed")], default="new", max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["-created_at"]}),
    ]
