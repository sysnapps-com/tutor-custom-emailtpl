"""
Fixture-based render tests for the 8 in-scope families.

Covers:
  1. Each of the 5 components renders without error using the verified
     fixture context in fixtures.py.
  2. A plaintext alternative always accompanies the HTML body (safety
     requirement: no HTML-only overrides).
  3. Every family renders under multiple active languages without raising
     -- proving the packaged templates' {% load i18n %} / {% trans %} /
     {% blocktrans %} usage is structurally sound for multi-language
     sites, independent of whether real .mo catalogs exist for those
     languages in this test environment.
  4. A rendered family can be sent (sync, locmem backend) and under
     Celery's eager-execution mode.

These tests intentionally do NOT invoke edx-platform's own `ace.send()` or
`send_mail_to_student()` -- this package does not vendor edx-platform.
"""
import os

from django.core import mail
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.utils import translation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emailtpl_app.tests.test_settings")

from .fixtures import FAMILY_CONTEXTS  # noqa: E402

FAMILY_TEMPLATE_PREFIXES = {
    "instructor:accountcreationandenrollment": "instructor/edx_ace/accountcreationandenrollment/email",
    "instructor:allowedenroll": "instructor/edx_ace/allowedenroll/email",
    "instructor:allowedunenroll": "instructor/edx_ace/allowedunenroll/email",
    "instructor:enrollenrolled": "instructor/edx_ace/enrollenrolled/email",
    "instructor:enrolledunenroll": "instructor/edx_ace/enrolledunenroll/email",
    "instructor:addbetatester": "instructor/edx_ace/addbetatester/email",
    "instructor:removebetatester": "instructor/edx_ace/removebetatester/email",
    "support:wholecoursereset": "support/edx_ace/wholecoursereset/email",
}

COMPONENTS = ("from_name.txt", "subject.txt", "body.html", "head.html", "body.txt")


def _render_family(prefix, context):
    rendered = {}
    for component in COMPONENTS:
        tmpl = get_template(f"{prefix}/{component}")
        text = tmpl.render(context)
        # Real ACE rendering strips surrounding whitespace from single-line
        # components (subject/from_name) before using them as mail headers;
        # do the same here so a trailing template newline doesn't produce
        # an invalid header during the locmem/email.message() validation.
        if component in ("subject.txt", "from_name.txt"):
            text = text.strip()
        rendered[component] = text
    return rendered


class RenderAllFamiliesTest(TestCase):
    """Renders every component of every in-scope family."""

    def test_all_eight_families_render_all_five_components(self):
        for family_key, prefix in FAMILY_TEMPLATE_PREFIXES.items():
            with self.subTest(family=family_key):
                rendered = _render_family(prefix, FAMILY_CONTEXTS[family_key])
                for component in COMPONENTS:
                    self.assertTrue(
                        rendered[component] is not None,
                        f"{family_key}/{component} failed to render",
                    )

    def test_no_family_is_html_only(self):
        for family_key, prefix in FAMILY_TEMPLATE_PREFIXES.items():
            with self.subTest(family=family_key):
                rendered = _render_family(prefix, FAMILY_CONTEXTS[family_key])
                self.assertTrue(rendered["body.txt"].strip(), f"{family_key} has no plaintext body")
                self.assertTrue(rendered["body.html"].strip(), f"{family_key} has no HTML body")


class MultiLanguageRenderTest(TestCase):
    """Proves every family renders cleanly with a non-default language active.

    This does not assert the *translated* text (no .mo catalogs are built
    for this standalone test environment) -- it asserts that activating a
    different language and rendering does not raise, which is what a
    packaged template with correct {% load i18n %} usage should guarantee
    regardless of catalog completeness (untranslated strings simply fall
    back to the source language).
    """

    def test_all_families_render_under_every_configured_language(self):
        from django.conf import settings

        for lang_code, _label in settings.LANGUAGES:
            with translation.override(lang_code):
                for family_key, prefix in FAMILY_TEMPLATE_PREFIXES.items():
                    with self.subTest(family=family_key, language=lang_code):
                        rendered = _render_family(prefix, FAMILY_CONTEXTS[family_key])
                        self.assertTrue(rendered["subject.txt"].strip())


class SendViaLocmemBackendTest(TestCase):
    """Proves a rendered family can actually be sent (sync, locmem backend)."""

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_each_family_synchronously(self):
        for family_key, prefix in FAMILY_TEMPLATE_PREFIXES.items():
            with self.subTest(family=family_key):
                rendered = _render_family(prefix, FAMILY_CONTEXTS[family_key])
                mail.send_mail(
                    subject=rendered["subject.txt"],
                    message=rendered["body.txt"],
                    from_email=f"{rendered['from_name.txt']} <no-reply@example.tld>",
                    recipient_list=["learner@example.tld"],
                )
        self.assertEqual(len(mail.outbox), len(FAMILY_TEMPLATE_PREFIXES))


class SendViaCeleryEagerTest(TestCase):
    """Proves the same send path works under Celery eager mode.

    Uses a local no-op task rather than importing edx-platform's ACE task,
    since this package does not vendor edx-platform.
    """

    def test_eager_task_sends_all_families(self):
        try:
            from celery import shared_task
        except ImportError:
            self.skipTest("celery not installed in this environment")

        @shared_task
        def _send_family(family_key, prefix, context):
            rendered = _render_family(prefix, context)
            return mail.send_mail(
                subject=rendered["subject.txt"],
                message=rendered["body.txt"],
                from_email="no-reply@example.tld",
                recipient_list=["learner@example.tld"],
            )

        with override_settings(
            CELERY_TASK_ALWAYS_EAGER=True,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ):
            mail.outbox = []
            for family_key, prefix in FAMILY_TEMPLATE_PREFIXES.items():
                _send_family.delay(family_key, prefix, FAMILY_CONTEXTS[family_key])
            self.assertEqual(len(mail.outbox), len(FAMILY_TEMPLATE_PREFIXES))


class CsvAutomatedSignupsWelcomeEmailTest(TestCase):
    """Proves the plugin works with the legacy instructor-dashboard CSV
    "batch enrollment" auto-register/auto-enroll mechanism.

    This is the `instructor:accountcreationandenrollment` family, gated in
    edx-platform behind the ALLOW_AUTOMATED_SIGNUPS feature toggle
    (default off; see README "Legacy CSV auto-register/auto-enroll"). The
    context here uses the empirically-confirmed variable set -- course_name,
    site_name (bare domain), email_address, password, course_url -- rather
    than the placeholder names an earlier version of this plugin shipped.
    """

    def test_welcome_email_renders_with_generated_password(self):
        prefix = FAMILY_TEMPLATE_PREFIXES["instructor:accountcreationandenrollment"]
        context = FAMILY_CONTEXTS["instructor:accountcreationandenrollment"]
        rendered = _render_family(prefix, context)

        # The whole point of this family: the generated password must
        # actually appear in the sent body, not render blank.
        self.assertIn(context["password"], rendered["body.txt"])
        # body.html correctly HTML-escapes special characters (matching
        # upstream's own {% filter force_escape %} behavior) -- a browser
        # renders &amp; back to & visually, so check for the escaped form
        # here rather than asserting the literal raw password string.
        from django.utils.html import escape
        self.assertIn(escape(context["password"]), rendered["body.html"])
        self.assertIn(context["course_name"], rendered["body.txt"])
        self.assertIn(context["email_address"], rendered["body.txt"])
        # site_name is used as a bare domain directly after "https://" in
        # the real upstream template -- prove that composition renders a
        # well-formed, non-empty URL rather than "https://" alone.
        self.assertIn(f"https://{context['site_name']}", rendered["body.txt"])

    def test_welcome_email_sends_successfully(self):
        prefix = FAMILY_TEMPLATE_PREFIXES["instructor:accountcreationandenrollment"]
        context = FAMILY_CONTEXTS["instructor:accountcreationandenrollment"]
        rendered = _render_family(prefix, context)

        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mail.outbox = []
            mail.send_mail(
                subject=rendered["subject.txt"],
                message=rendered["body.txt"],
                from_email=f"{rendered['from_name.txt']} <no-reply@example.tld>",
                recipient_list=[context["email_address"]],
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn(context["password"], mail.outbox[0].body)
