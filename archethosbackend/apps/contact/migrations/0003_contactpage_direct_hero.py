import django.db.models.deletion
from django.db import migrations, models


def copy_selected_slider_into_hero(apps, schema_editor):
    ContactPage = apps.get_model("contact", "ContactPage")
    Slider = apps.get_model("home", "Slider")
    for page in ContactPage.objects.exclude(slider_id=None):
        slider = Slider.objects.filter(pk=page.slider_id).first()
        if not slider:
            continue
        page.hero_eyebrow = slider.eyebrow
        page.hero_title = slider.title
        page.hero_description = slider.description
        page.hero_media_id = slider.media_id
        page.hero_primary_cta_label = slider.primary_cta_label
        page.hero_primary_cta_url = slider.primary_cta_url
        page.hero_secondary_cta_label = slider.secondary_cta_label
        page.hero_secondary_cta_url = slider.secondary_cta_url
        page.save(update_fields=[
            "hero_eyebrow", "hero_title", "hero_description", "hero_media",
            "hero_primary_cta_label", "hero_primary_cta_url", "hero_secondary_cta_label",
            "hero_secondary_cta_url",
        ])


class Migration(migrations.Migration):
    dependencies = [("contact", "0002_contactpage_next_section")]

    operations = [
        migrations.AddField(model_name="contactpage", name="hero_eyebrow", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="contactpage", name="hero_title", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="contactpage", name="hero_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="contactpage", name="hero_media", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contact_hero_media", to="media_library.mediaasset")),
        migrations.AddField(model_name="contactpage", name="hero_primary_cta_label", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="contactpage", name="hero_primary_cta_url", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="contactpage", name="hero_secondary_cta_label", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="contactpage", name="hero_secondary_cta_url", field=models.CharField(blank=True, max_length=255)),
        migrations.RunPython(copy_selected_slider_into_hero, migrations.RunPython.noop),
        migrations.RemoveField(model_name="contactpage", name="slider"),
    ]
