"""
Hero gains a rendering variant, and slides gain a second call to action.

Written by hand rather than generated: `makemigrations` sees `cta_label` gone
and `primary_cta_label` arrived and asks whether it is a rename. Answering that
prompt is what preserves the existing values, so the RenameField operations are
spelled out here instead of letting a non-interactive run drop and re-add the
columns.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("sections", "0001_initial")]

    operations = [
        # Which hero component renders this. A variant rather than a second
        # section type, because both take the same fields.
        migrations.AddField(
            model_name="herosection",
            name="variant",
            field=models.CharField(
                choices=[
                    ("SLIDER", "Slider — several frames"),
                    ("PHOTOGRAPHIC", "Photographic — a single frame"),
                ],
                default="SLIDER",
                max_length=16,
            ),
        ),
        # The single CTA becomes the primary one; values carry over.
        migrations.RenameField(
            model_name="heroslide", old_name="cta_label", new_name="primary_cta_label"
        ),
        migrations.RenameField(
            model_name="heroslide", old_name="cta_url", new_name="primary_cta_url"
        ),
        migrations.AddField(
            model_name="heroslide",
            name="secondary_cta_label",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="secondary_cta_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
