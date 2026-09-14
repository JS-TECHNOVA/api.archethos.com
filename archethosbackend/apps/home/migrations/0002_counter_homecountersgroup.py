import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0001_initial")]

    operations = [
        migrations.CreateModel(name="Counter", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("value", models.CharField(max_length=50)), ("label", models.CharField(max_length=255)),
            ("description", models.TextField(blank=True)), ("order", models.PositiveIntegerField(default=0)),
            ("is_visible", models.BooleanField(default=True)),
        ], options={"ordering": ["order", "id"]}),
        migrations.CreateModel(name="HomeCountersGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)), ("description", models.TextField(blank=True)),
            ("counters", models.ManyToManyField(blank=True, related_name="home_counter_groups", to="home.counter")),
            ("page", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="counters_group", to="home.homepage")),
        ]),
    ]
