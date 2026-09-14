import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("about", "0001_initial"), ("home", "0003_workprocessgroup_workprocessstep_homepage_direct_selections")]

    operations = [
        migrations.AddField(
            model_name="aboutpage",
            name="work_process_group",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_pages", to="home.workprocessgroup"),
        ),
    ]
