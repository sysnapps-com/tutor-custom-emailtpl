"""
Tutor plugin entry point for tutor-custom-emailtpl.

This plugin:

- Defines the EMAILTPL_* configuration values.
- Installs this distribution into the Open edX image during image build.
- Registers emailtpl_app as a Django application.
- Prepends emailtpl_app/templates to Django's template search directories,
  allowing its ACE template files to override upstream edx-platform files.

Target: Tutor v22 / Open edX Verawood.
"""

from tutor import hooks

PLUGIN_NAME = "emailtpl"
CONFIG_PREFIX = PLUGIN_NAME.upper()

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        (
            f"{CONFIG_PREFIX}_ENABLED",
            True,
        ),
        (
            f"{CONFIG_PREFIX}_FAIL_OPEN_TO_UPSTREAM",
            True,
        ),
        (
            f"{CONFIG_PREFIX}_INSTALL_SOURCE",
            "pypi",
        ),
        (
            f"{CONFIG_PREFIX}_SUPPORTED_LANGUAGES",
            ["en"],
        ),
    ]
)

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        r"""
{%- if EMAILTPL_INSTALL_SOURCE == "pypi" %}
# tutor-custom-emailtpl: install the Django app in the Open edX image.
RUN pip install tutor-custom-emailtpl
{%- elif EMAILTPL_INSTALL_SOURCE != "none" %}
# EMAILTPL_INSTALL_SOURCE may be a VCS URL, private-index requirement,
# local wheel URL, or other pip-compatible requirement specifier.
RUN pip install "{{ EMAILTPL_INSTALL_SOURCE }}"
{%- endif %}
""",
    )
)

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-common-settings",
        r"""
# tutor-custom-emailtpl: register the Django app and ACE email-template
# override directory. This modifies only INSTALLED_APPS and an existing
# Django template engine's DIRS list. It does not modify DATABASES.

if {{ EMAILTPL_ENABLED }}:
    import os as _emailtpl_os
    import emailtpl_app as _emailtpl_app_module

    if "emailtpl_app" not in INSTALLED_APPS:
        INSTALLED_APPS.append("emailtpl_app")

    _emailtpl_template_dir = _emailtpl_os.path.join(
        _emailtpl_os.path.dirname(_emailtpl_app_module.__file__),
        "templates",
    )

    for _emailtpl_template_engine in TEMPLATES:
        if _emailtpl_template_engine.get(
            "BACKEND"
        ) == "django.template.backends.django.DjangoTemplates":
            _emailtpl_template_engine.setdefault("DIRS", [])

            if (
                _emailtpl_template_dir
                not in _emailtpl_template_engine["DIRS"]
            ):
                _emailtpl_template_engine["DIRS"].insert(
                    0,
                    _emailtpl_template_dir,
                )

            break
""",
    )
)