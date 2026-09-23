"""Django AppConfig for the enrollment/instructor email template override app
(part of the tutor-custom-emailtpl plugin).

Scope (v1): the "Enrollment and instructor operations" ACE message family
only. See README.md for the full list of families this app does NOT yet
cover (Accounts/Authentication, Course communication/schedules,
Discussions, Notifications, Certificates, Bulk email, Commerce).
"""
from django.apps import AppConfig


class EmailTplAppConfig(AppConfig):
    name = "emailtpl_app"
    verbose_name = "Custom Email Templates (Enrollment/Instructor)"
    default_auto_field = "django.db.models.BigAutoField"

    # The 8 in-scope ACE message families and their upstream-relative
    # template name prefixes (relative to the "lms/templates" DIRS root --
    # see docs/TEMPLATE_VARIABLES.md and README "Open assumptions" for the
    # confidence level behind this base path).
    SUPPORTED_FAMILIES = {
        "instructor:accountcreationandenrollment": "instructor/edx_ace/accountcreationandenrollment/email",
        "instructor:allowedenroll": "instructor/edx_ace/allowedenroll/email",
        "instructor:allowedunenroll": "instructor/edx_ace/allowedunenroll/email",
        "instructor:enrollenrolled": "instructor/edx_ace/enrollenrolled/email",
        "instructor:enrolledunenroll": "instructor/edx_ace/enrolledunenroll/email",
        "instructor:addbetatester": "instructor/edx_ace/addbetatester/email",
        "instructor:removebetatester": "instructor/edx_ace/removebetatester/email",
        "support:wholecoursereset": "support/edx_ace/wholecoursereset/email",
    }

    # Families whose context-variable contract is directly documented in
    # edx-platform's own docstrings (lms.djangoapps.instructor.enrollment.
    # send_mail_to_student), vs. families where the plugin's context
    # variables are a best-effort inference. See docs/TEMPLATE_VARIABLES.md.
    #
    # NOTE: "verified" here means the family's context is grounded in a
    # citable source (docstring, source template, or live-instance
    # testing) -- it does not mean every family was independently
    # source-inspected. `accountcreationandenrollment` is the only family
    # directly confirmed against both edx-platform's packaged template
    # source and a live Verawood test; the other 6 `instructor:*` families
    # are included here on the strength of sharing the exact same
    # `param_dict` contract, not individual inspection.
    VERIFIED_CONTEXT_FAMILIES = {
        "instructor:accountcreationandenrollment",
        "instructor:allowedenroll",
        "instructor:allowedunenroll",
        "instructor:enrollenrolled",
        "instructor:enrolledunenroll",
        "instructor:addbetatester",
        "instructor:removebetatester",
    }
    UNVERIFIED_CONTEXT_FAMILIES = {"support:wholecoursereset"}

    # Explicitly NOT in scope for v1 -- do not add templates for these here.
    NOT_YET_SUPPORTED = [
        "Accounts / Authentication",
        "Course communication / Schedules",
        "Discussions",
        "Notifications",
        "Certificates",
        "Bulk email",
        "Commerce / Subscriptions",
    ]

    COMPONENTS = ("from_name.txt", "subject.txt", "body.html", "head.html", "body.txt")

    def ready(self):
        # Import signal handlers / registry validators lazily here if added later.
        pass
