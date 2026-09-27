from django.db import migrations, models


def move_next_content_into_section(apps, schema_editor):
    ContactPage = apps.get_model("contact", "ContactPage")
    for page in ContactPage.objects.all():
        page.next_section = {
            "eyebrow": page.next_eyebrow,
            "title": page.next_title,
            "items": page.next_steps if isinstance(page.next_steps, list) else [],
        }
        page.save(update_fields=["next_section"])


class Migration(migrations.Migration):
    dependencies = [("contact", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="contactpage",
            name="next_section",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(move_next_content_into_section, migrations.RunPython.noop),
        migrations.RemoveField(model_name="contactpage", name="next_eyebrow"),
        migrations.RemoveField(model_name="contactpage", name="next_title"),
        migrations.RemoveField(model_name="contactpage", name="next_steps"),
    ]
