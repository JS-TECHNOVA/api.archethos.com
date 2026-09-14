from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_company_whatsapp_link_enquiry"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(model_name="company", name="smtp_host", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="company", name="smtp_port", field=models.PositiveIntegerField(default=587)),
        migrations.AddField(model_name="company", name="smtp_username", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="company", name="smtp_password", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="company", name="smtp_from_email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="company", name="smtp_use_tls", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="company", name="smtp_use_ssl", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="enquiry", name="archived", field=models.BooleanField(default=False)),
        migrations.AlterField(model_name="enquiry", name="status", field=models.CharField(choices=[("unread", "Unread"), ("read", "Read"), ("replied", "Replied")], default="unread", max_length=20)),
        migrations.CreateModel(name="EnquiryReply", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("subject", models.CharField(max_length=255)), ("message", models.TextField()), ("to_email", models.EmailField(max_length=254)), ("sent_at", models.DateTimeField(auto_now_add=True)),
            ("enquiry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="core.enquiry")),
            ("sent_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="enquiry_replies", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-sent_at"]}),
    ]
