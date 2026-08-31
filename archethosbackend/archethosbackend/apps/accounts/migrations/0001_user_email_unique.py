"""
Case-insensitive unique index on auth_user.email.

Django's built-in User does not make email unique, but the CMS logs in by email.
Without this index two accounts could share an address and login would be
ambiguous. Enforced in the database so it holds regardless of which code path
creates the user (API, Django Admin, shell, createsuperuser).

Blank emails are excluded so accounts without one (e.g. a bootstrap superuser)
do not collide with each other.
"""

from django.db import migrations

CREATE = """
CREATE UNIQUE INDEX auth_user_email_ci_unique
ON auth_user (LOWER(email))
WHERE email <> '';
"""

DROP = "DROP INDEX IF EXISTS auth_user_email_ci_unique;"


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE, reverse_sql=DROP),
    ]
