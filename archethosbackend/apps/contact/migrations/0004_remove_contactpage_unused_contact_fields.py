from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("contact", "0003_contactpage_direct_hero")]

    operations = [
        migrations.RemoveField(model_name="contactpage", name="hero_primary_cta_label"),
        migrations.RemoveField(model_name="contactpage", name="hero_primary_cta_url"),
        migrations.RemoveField(model_name="contactpage", name="hero_secondary_cta_label"),
        migrations.RemoveField(model_name="contactpage", name="hero_secondary_cta_url"),
        migrations.RemoveField(model_name="contactpage", name="form_eyebrow"),
    ]
