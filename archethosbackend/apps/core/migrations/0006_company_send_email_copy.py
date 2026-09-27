from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_company_footer_other_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="send_email_copy",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
