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
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-common-settings",
        """
# tutor-custom-emailtpl: enrollment/instructor ACE email template overrides.
if {{ EMAILTPL_ENABLED }}:
    INSTALLED_APPS.append("emailtpl_app")

    import emailtpl_app
    _EMAILTPL_TEMPLATE_DIR = os.path.join(
        os.path.dirname(emailtpl_app.__file__), "templates"
    )

    # Locate the Django (not Mako) template engine by BACKEND rather than
    # assuming TEMPLATES[0] -- Ulmo/Verawood's common.py is documented as
    # configuring more than one engine (see README "Open assumptions").
    for _engine in TEMPLATES:
        if _engine.get("BACKEND") == "django.template.backends.django.DjangoTemplates":
            _engine["DIRS"].insert(0, _EMAILTPL_TEMPLATE_DIR)
            break
    else:
        raise RuntimeError(
            "tutor-custom-emailtpl: no django.template.backends.django.DjangoTemplates "
            "engine found in TEMPLATES; cannot install override DIRS."
        )
""",
    )
)
