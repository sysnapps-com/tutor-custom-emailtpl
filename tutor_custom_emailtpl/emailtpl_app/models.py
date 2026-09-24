"""
Registry model letting an administrator supply custom subject/HTML/text/
from-name content for each of the 8 in-scope ACE message families, per
language.

v1.1 change: added `language` so a site running multiple learner
languages can store one override per (family, language) pair rather than
one override forced onto every locale. The *packaged* template files
(under templates/) are not per-language copies -- they use Django's
{% trans %} / {% blocktrans %} tags so a single file renders correctly in
whichever language is active at send time, exactly like upstream
edx-platform templates do. The registry model is for admin-authored
free-text content, which Django's translation machinery cannot
auto-translate for you, hence the explicit `language` column here.

v1 scope note (unchanged): this model is intentionally *not* scoped by
organization or course. The `enrollment.py` context does carry a course
`org` value that a future version could use for per-org overrides, so the
model below reserves `organization_slug` and `course_key` as nullable
fields set to "" in v1.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def _default_language():
    return getattr(settings, "LANGUAGE_CODE", "en")


class EmailFamilyOverride(models.Model):
    """One customized ACE message family, for one language (all 5
    components together).

    Exactly one *active* row should exist per (family_key, language) pair
    in v1 (enforced by unique_together with the reserved, always-blank
    scope fields so the schema is already shaped for future per-org/
    per-course rows).
    """

    FAMILY_CHOICES = [
        ("instructor:accountcreationandenrollment", "Create account and enroll"),
        ("instructor:allowedenroll", "Allowed to enroll"),
        ("instructor:allowedunenroll", "Allowed unenroll"),
        ("instructor:enrollenrolled", "Enroll already-enrolled user"),
        ("instructor:enrolledunenroll", "Unenroll existing user"),
        ("instructor:addbetatester", "Add beta tester"),
        ("instructor:removebetatester", "Remove beta tester"),
        ("support:wholecoursereset", "Whole course reset"),
    ]

    family_key = models.CharField(max_length=64, choices=FAMILY_CHOICES)

    # BCP-47 / Django language code, e.g. "en", "es", "es-419", "fr-ca".
    # Defaults to the platform's LANGUAGE_CODE so a site that only ever
    # customizes its default locale doesn't have to think about this field.
    language = models.CharField(max_length=32, default=_default_language)

    # Reserved for a future release; always blank/NULL in v1. Kept now so
    # extending scope later does not require a breaking migration.
    organization_slug = models.CharField(max_length=255, blank=True, default="")
    course_key = models.CharField(max_length=255, blank=True, default="")

    from_name = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255)
    body_html = models.TextField(help_text="Must have a body_text counterpart -- HTML-only overrides are rejected.")
    body_text = models.TextField()
    head_html = models.TextField(blank=True, default="")

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("family_key", "language", "organization_slug", "course_key")
        verbose_name = "Email family override"

    def clean(self):
        # Safety requirement: never allow an HTML-only override; a plaintext
        # alternative must always accompany the HTML body.
        if self.body_html and not self.body_text.strip():
            raise ValidationError(
                "body_text is required whenever body_html is set "
                "(plaintext alternative may not be omitted)."
            )

    def __str__(self):
        return f"{self.family_key} [{self.language}] (active={self.is_active})"
