from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("created", "Created"), ("updated", "Updated"), ("deleted", "Deleted")], max_length=16)),
                ("resource", models.CharField(max_length=100)),
                ("object_id", models.CharField(blank=True, max_length=64)),
                ("object_repr", models.CharField(max_length=255)),
                ("changed_fields", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="auditlog", index=models.Index(fields=["-created_at"], name="accounts_au_created_05a053_idx")),
        migrations.AddIndex(model_name="auditlog", index=models.Index(fields=["action", "-created_at"], name="accounts_au_action_9b1ff7_idx")),
    ]
