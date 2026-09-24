"""
Tutor plugin entry point for tutor-custom-emailtpl.

Registers:
  - config defaults (enable flag, fail-open flag, install-source flag,
    and a supported-languages hint used only for the diagnostic command)
  - a Dockerfile patch that installs this same distribution into the
    openedx (LMS/CMS) image, so `emailtpl_app` is importable there
  - an `openedx-common-settings` env patch that adds `emailtpl_app`
    to INSTALLED_APPS and prepends its template directory to the Django
    engine's DIRS (located by BACKEND, not assumed to be index 0)

Minimum supported release / Tutor version: see README.md. This plugin
targets Verawood (Tutor v22.x) by default; see README "Ulmo compatibility"
for the older Tutor v21.x / Ulmo pin.
"""
from tutor import hooks

PLUGIN_NAME = "emailtpl"
CONFIG_PREFIX = PLUGIN_NAME.upper()  # "EMAILTPL"

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        (f"{CONFIG_PREFIX}_ENABLED", True),
        # If a rendered template is somehow missing at runtime, fail open to
        # the upstream edx-platform template rather than raising -- this
        # governs the plugin's own defensive get_template() usage, not
        # Django's built-in loader fallback (which already falls through to
        # app-template loaders when DIRS misses).
        (f"{CONFIG_PREFIX}_FAIL_OPEN_TO_UPSTREAM", True),
        # How this package reaches the image at build time. "pypi" does
        # `pip install tutor-custom-emailtpl`; "none" skips the Dockerfile
        # patch entirely so an operator can wire up their own install step
        # (e.g. a private index, a VCS ref, or a local wheel via a mount).
        (f"{CONFIG_PREFIX}_INSTALL_SOURCE", "pypi"),
        # Informational only, consumed by the check_email_templates
        # --language flag's callers / by an operator's own tooling -- NOT
        # enforced anywhere in the render path. Django will happily render
        # a template in any language whose catalog is installed regardless
        # of this list; this exists so `tutor config printvalue
        # EMAILTPL_SUPPORTED_LANGUAGES` gives a documented answer to "which
        # languages has this operator actually checked".
        (f"{CONFIG_PREFIX}_SUPPORTED_LANGUAGES", ["en"]),
    ]
)

# --- Install the Django app into the openedx image -------------------------
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        """
{%- if EMAILTPL_INSTALL_SOURCE == "pypi" %}
# tutor-custom-emailtpl: install this plugin's Django app into the
# openedx image so `emailtpl_app` is importable by LMS/CMS.
RUN pip install tutor-custom-emailtpl
{%- elif EMAILTPL_INSTALL_SOURCE != "none" %}
# tutor-custom-emailtpl: EMAILTPL_INSTALL_SOURCE is set to a custom value;
# treat it as a pip-installable requirement spec (VCS URL, private index
# package, etc).
RUN pip install "{{ EMAILTPL_INSTALL_SOURCE }}"
{%- endif %}
""",
    )
)

# --- Wire the Django app + template DIRS into LMS/CMS settings -------------
#
# SAFETY (see README "Open assumptions" / bug report on DATABASES corruption):
# this patch must NEVER raise. It runs inside edx-platform's own generated
# settings module, sharing that module's global namespace with everything
# else the module still has left to execute after this patch's insertion
# point -- including, in some renderings, DATABASES construction further
# down the same file. An uncaught exception here aborts the rest of that
# module's execution silently from Django's perspective (no import-time
# traceback is guaranteed to surface before something later tries to use a
# half-initialized settings module), which is the leading suspect behind
# DATABASES ending up incomplete when this plugin is enabled. Accordingly:
#   - never assign to DATABASES or TEMPLATES wholesale
#   - never raise; a missing engine or an already-present entry is a no-op,
#     not an error (EMAILTPL_FAIL_OPEN_TO_UPSTREAM governs *diagnostics*
#     via check_email_templates, not settings-import behavior, which must
#     always fail open)
#   - explicit `import os` -- never assume it's already in scope
#   - idempotent: guard INSTALLED_APPS append and DIRS insert so re-running
#     this block (e.g. if a future Tutor version applies patches twice, or
#     LMS/CMS share the rendered module) never duplicates entries
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-common-settings",
        """
# tutor-custom-emailtpl: enrollment/instructor ACE email template overrides.
# This block must never raise -- see plugin.py comment above add_item() for why.
if {{ EMAILTPL_ENABLED }}:
    import os as _emailtpl_os

    if "emailtpl_app" not in INSTALLED_APPS:
        INSTALLED_APPS.append("emailtpl_app")

    try:
        import emailtpl_app as _emailtpl_app_module

        _EMAILTPL_TEMPLATE_DIR = _emailtpl_os.path.join(
            _emailtpl_os.path.dirname(_emailtpl_app_module.__file__), "templates"
        )

        # Locate the Django (not Mako) template engine by BACKEND rather than
        # assuming TEMPLATES[0] -- Ulmo/Verawood's common.py is documented as
        # configuring more than one engine (see README "Open assumptions").
        # Mutates the existing engine dict's DIRS list in place; TEMPLATES
        # itself is never reassigned, and every pre-existing entry is kept.
        for _emailtpl_engine in TEMPLATES:
            if _emailtpl_engine.get("BACKEND") == "django.template.backends.django.DjangoTemplates":
                _emailtpl_engine.setdefault("DIRS", [])
                if _EMAILTPL_TEMPLATE_DIR not in _emailtpl_engine["DIRS"]:
                    _emailtpl_engine["DIRS"].insert(0, _EMAILTPL_TEMPLATE_DIR)
                break
        # No matching engine: fail open (skip the override) rather than raise.
        # Diagnose this case with `check_email_templates --strict` instead,
        # which is safe to fail loudly since it runs as a standalone command,
        # not inside settings import.

        del _emailtpl_engine
    except Exception:
        # Fail open unconditionally at settings-import time, regardless of
        # EMAILTPL_FAIL_OPEN_TO_UPSTREAM -- an exception here must never be
        # allowed to corrupt the rest of this settings module's execution.
        pass

    del _emailtpl_os
""",
    )
)