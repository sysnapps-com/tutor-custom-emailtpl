from django.db import migrations, models

import emailtpl_app.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailFamilyOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("family_key", models.CharField(choices=[
                    ("instructor:accountcreationandenrollment", "Create account and enroll"),
                    ("instructor:allowedenroll", "Allowed to enroll"),
                    ("instructor:allowedunenroll", "Allowed unenroll"),
                    ("instructor:enrollenrolled", "Enroll already-enrolled user"),
                    ("instructor:enrolledunenroll", "Unenroll existing user"),
                    ("instructor:addbetatester", "Add beta tester"),
                    ("instructor:removebetatester", "Remove beta tester"),
                    ("support:wholecoursereset", "Whole course reset"),
                ], max_length=64)),
                ("language", models.CharField(default=emailtpl_app.models._default_language, max_length=32)),
                ("organization_slug", models.CharField(blank=True, default="", max_length=255)),
                ("course_key", models.CharField(blank=True, default="", max_length=255)),
                ("from_name", models.CharField(blank=True, max_length=255)),
                ("subject", models.CharField(max_length=255)),
                ("body_html", models.TextField(help_text="Must have a body_text counterpart -- HTML-only overrides are rejected.")),
                ("body_text", models.TextField()),
                ("head_html", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Email family override"},
        ),
        migrations.AlterUniqueTogether(
            name="emailfamilyoverride",
            unique_together={("family_key", "language", "organization_slug", "course_key")},
        ),
    ]
