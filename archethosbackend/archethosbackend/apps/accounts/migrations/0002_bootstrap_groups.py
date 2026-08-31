"""Create the four default CMS roles (see accounts/groups.py)."""

from django.db import migrations

from archethosbackend.apps.accounts.groups import GROUPS, sync_groups


def create_groups(apps, schema_editor):
    sync_groups(apps.get_model("auth", "Group"), apps.get_model("auth", "Permission"))


def delete_groups(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_user_email_unique"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
