from django.db import migrations, models


def copy_who_we_are_description(apps, schema_editor):
    AboutPage = apps.get_model("about", "AboutPage")
    for page in AboutPage.objects.all():
        value = page.who_we_are_description
        page.who_we_are_editor_data = value if isinstance(value, dict) else {
            "blocks": ([{"type": "paragraph", "data": {"text": value}}] if value else [])
        }
        page.save(update_fields=["who_we_are_editor_data"])


class Migration(migrations.Migration):
    dependencies = [("about", "0006_aboutpage_direct_hero")]

    operations = [
        migrations.AddField(
            model_name="aboutpage",
            name="who_we_are_editor_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(copy_who_we_are_description, migrations.RunPython.noop),
        migrations.RemoveField(model_name="aboutpage", name="who_we_are_description"),
        migrations.RenameField(model_name="aboutpage", old_name="who_we_are_editor_data", new_name="who_we_are_description"),
    ]
