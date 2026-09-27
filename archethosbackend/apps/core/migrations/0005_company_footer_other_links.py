from django.db import migrations, models


def move_legacy_footer_links(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    company = Company.objects.filter(pk=1).first()
    if not company:
        return

    groups = company.footer_links if isinstance(company.footer_links, list) else []
    other_links = company.footer_other_links if isinstance(company.footer_other_links, list) else []
    migrated_groups = []
    changed = False
    for group in groups:
        if not isinstance(group, dict):
            migrated_groups.append(group)
            continue
        clean_group = dict(group)
        legacy_links = clean_group.pop("other_link", [])
        if isinstance(legacy_links, list):
            other_links.extend(legacy_links)
        changed = changed or clean_group != group
        migrated_groups.append(clean_group)

    if changed:
        company.footer_links = migrated_groups
        company.footer_other_links = other_links
        company.save(update_fields=["footer_links", "footer_other_links"])


class Migration(migrations.Migration):
    dependencies = [("core", "0004_alter_enquiry_location_alter_enquiry_project_type")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="footer_other_links",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(move_legacy_footer_links, migrations.RunPython.noop),
    ]
