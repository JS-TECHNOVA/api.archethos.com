import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("about", "0002_aboutpage_work_process_group"), ("media_library", "0007_media_thumbnail_file")]

    operations = [
        migrations.RemoveConstraint(model_name="aboutgroup", name="about_page_group_type_unique"),
        migrations.AddField(model_name="aboutpage", name="studio_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="studio_title", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="studio_lead", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="studio_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="studio_supporting_text", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="studio_image", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_studio_images", to="media_library.mediaasset")),
        migrations.AddField(model_name="aboutpage", name="mission", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="vision", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="founder_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="founder_title", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="founder_message", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="aboutpage", name="founder_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="founder_role", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="founder_credentials", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="founder_image", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_founder_images", to="media_library.mediaasset")),
        migrations.AddField(model_name="aboutpage", name="philosophy_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="philosophy_title", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="philosophy_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="philosophy_supporting_text", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="philosophy_image", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_philosophy_images", to="media_library.mediaasset")),
        migrations.AddField(model_name="aboutpage", name="philosophy_cta_label", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="aboutpage", name="philosophy_cta_url", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="presence_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="presence_title", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="presence_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="presence_cta_label", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="aboutpage", name="presence_cta_url", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="cta_title", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="aboutpage", name="cta_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="aboutpage", name="cta_image", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="about_cta_images", to="media_library.mediaasset")),
        migrations.AddField(model_name="aboutpage", name="cta_label", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="aboutpage", name="cta_url", field=models.CharField(blank=True, max_length=255)),
        migrations.DeleteModel(name="AboutGroup"),
    ]
