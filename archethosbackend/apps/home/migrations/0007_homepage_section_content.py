from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0006_remove_homecountersgroup_counters_and_more")]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="section_content",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
