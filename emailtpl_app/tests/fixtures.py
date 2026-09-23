"""
Realistic-shaped context values for the 8 in-scope families.

Confidence tiers (see docs/TEMPLATE_VARIABLES.md for full citations):

1. `instructor:accountcreationandenrollment` -- EMPIRICALLY CONFIRMED.
   Directly inspected against edx-platform's own packaged template
   (lms/templates/instructor/edx_ace/accountcreationandenrollment/email/
   body.html on the openedx-platform master branch) AND confirmed working
   against a live Verawood instance with ALLOW_AUTOMATED_SIGNUPS enabled
   (the instructor-dashboard "Batch Enrollment" CSV upload feature). Real
   keys: course_name, site_name (used as a bare domain, e.g. after
   "https://", not a display name), email_address, password, course_url.

2. The other 6 `instructor:*` families -- HIGH-CONFIDENCE BY ANALOGY, not
   individually source-inspected this session. They share the exact same
   `param_dict` contract (built by the same `get_email_params()` /
   `send_mail_to_student()` path in enrollment.py) as
   accountcreationandenrollment. Since that family's real template key is
   `course_name` (not the `display_name` the docstring's prose described),
   these 6 are treated as using `course_name` too, on the same evidence.
   `password` is NOT included for these 6 -- they act on already-existing
   accounts (enroll/unenroll/beta-add/beta-remove), so there is no new
   password to report.

3. `support:wholecoursereset` -- still UNVERIFIED. Built by a separate
   code path (lms.djangoapps.support), not enrollment.py, and not
   inspected this session.

`site_name` is used as a bare domain string (e.g. "example.tld") because
that's how the real accountcreationandenrollment template consumes it
(directly after "https://"), not as a human-readable platform name.
"""

VERIFIED_INSTRUCTOR_CONTEXT = {
    "site_name": "example.tld",
    "course_name": "Sample Course: Intro to Testing",
    "course_id": "course-v1:Org+CS101+2026",
    "course_url": "https://example.tld/courses/course-v1:Org+CS101+2026/course/",
    "registration_url": "https://example.tld/register",
    "auto_enroll": "False",
    "user_id": 42,
    "email_address": "learner@example.tld",
    "full_name": "Ada Learner",
    "is_shib_course": False,
}

FAMILY_CONTEXTS = {
    # Tier 1: empirically confirmed, includes `password` (new-account family only).
    "instructor:accountcreationandenrollment": {
        **VERIFIED_INSTRUCTOR_CONTEXT,
        "password": "Tr0ub4dor&3xample",  # fixture value only, never a real credential
        "message_type": "account_creation_and_enrollment",
    },
    # Tier 2: high-confidence by analogy (course_name confirmed via family above;
    # no `password` -- these act on existing accounts).
    "instructor:allowedenroll": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "allowed_enroll"},
    "instructor:allowedunenroll": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "allowed_unenroll"},
    "instructor:enrollenrolled": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "enrolled_enroll"},
    "instructor:enrolledunenroll": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "enrolled_unenroll"},
    "instructor:addbetatester": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "add_beta_tester"},
    "instructor:removebetatester": {**VERIFIED_INSTRUCTOR_CONTEXT, "message_type": "remove_beta_tester"},
    # Tier 3: unverified context (see module docstring above).
    "support:wholecoursereset": {
        "site_name": "example.tld",
        "course_name": "Sample Course: Intro to Testing",
        "course_id": "course-v1:Org+CS101+2026",
        "course_url": "https://example.tld/courses/course-v1:Org+CS101+2026/course/",
        "full_name": "Ada Learner",
    },
}
