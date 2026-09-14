import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0003_workprocessgroup_workprocessstep_homepage_direct_selections")]

    operations = [
        migrations.CreateModel(name="HomeContentGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("group_type", models.CharField(choices=[("intro", "Studio introduction"), ("design_build", "Design and build"), ("vastu", "Vastu preview"), ("locations", "Locations preview"), ("cta", "CTA")], max_length=30)),
            ("eyebrow", models.CharField(blank=True, max_length=255)), ("title", models.CharField(blank=True, max_length=255)),
            ("description", models.TextField(blank=True)), ("content", models.JSONField(blank=True, default=dict)),
            ("cta_label", models.CharField(blank=True, max_length=100)), ("cta_url", models.CharField(blank=True, max_length=255)), ("order", models.PositiveIntegerField(default=0)),
            ("media", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="home_content_group_media", to="media_library.mediaasset")),
            ("page", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_groups", to="home.homepage")),
            ("secondary_media", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="home_content_group_secondary_media", to="media_library.mediaasset")),
        ], options={"ordering": ["order", "id"]}),
        migrations.AddConstraint(model_name="homecontentgroup", constraint=models.UniqueConstraint(fields=("page", "group_type"), name="home_page_content_group_type_unique")),
    ]
