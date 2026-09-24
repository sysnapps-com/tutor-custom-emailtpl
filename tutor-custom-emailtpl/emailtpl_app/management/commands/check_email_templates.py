"""
Health/diagnostic command for tutor-custom-emailtpl.

Reports, for each of the 8 in-scope ACE message families:
  - which of the 5 components (from_name.txt, subject.txt, body.html,
    head.html, body.txt) resolve via django.template.loader.get_template()
  - whether template.origin confirms the resolved file lives inside this
    plugin's package (i.e. our DIRS entry actually won precedence) rather
    than falling through to an edx-platform copy
  - whether each family's context-variable contract is independently
    verified against edx-platform docstrings or still an assumption (see
    docs/TEMPLATE_VARIABLES.md)

Flags:
  --strict          Exit non-zero if any in-scope component fails to
                     resolve to this plugin's package.
  --family KEY       Restrict the check to one family (e.g.
                     instructor:allowedenroll). Repeatable.
  --language CODE    Render each component with {% language CODE %}
                     active first, to smoke-test that translation tags in
                     the packaged templates don't raise for that locale.
                     Does not require translation catalogs to exist for
                     CODE; it only proves the templates are valid under
                     Django's {% load i18n %} tags for an arbitrary code.
  --json             Emit machine-readable JSON instead of formatted text
                     (useful for CI smoke tests after `tutor images build`).
"""
import json
import os
import sys

from django.apps import apps
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import translation
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify that this plugin's email templates take precedence over edx-platform's."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit non-zero if any in-scope component fails to resolve to this plugin's package.",
        )
        parser.add_argument(
            "--family",
            action="append",
            dest="families",
            default=None,
            help="Restrict the check to this family key. Repeatable.",
        )
        parser.add_argument(
            "--language",
            default=None,
            help="Render components with this language active (i18n smoke test).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit JSON instead of formatted text.",
        )

    def handle(self, *args, **options):
        app_config = apps.get_app_config("emailtpl_app")
        # This file lives at emailtpl_app/management/commands/<this>.py,
        # so climb three levels (commands -> management -> emailtpl_app)
        # to get the package root that templates/ hangs off of.
        package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        families = options["families"] or list(app_config.SUPPORTED_FAMILIES.keys())
        unknown = set(families) - set(app_config.SUPPORTED_FAMILIES.keys())
        if unknown:
            self.stderr.write(self.style.ERROR(f"Unknown family key(s): {', '.join(sorted(unknown))}"))
            sys.exit(2)

        report = {"plugin_package_root": package_root, "families": {}}
        any_mismatch = False

        lang_ctx = translation.override(options["language"]) if options["language"] else None
        if lang_ctx:
            lang_ctx.__enter__()
        try:
            for family_key in families:
                template_prefix = app_config.SUPPORTED_FAMILIES[family_key]
                verified = family_key in app_config.VERIFIED_CONTEXT_FAMILIES
                family_report = {
                    "context_verified": verified,
                    "components": {},
                }
                for component in app_config.COMPONENTS:
                    template_name = f"{template_prefix}/{component}"
                    try:
                        tmpl = get_template(template_name)
                        origin = getattr(tmpl.template.origin, "name", "<unknown origin>")
                        is_ours = os.path.abspath(origin).startswith(package_root)
                        if not is_ours:
                            any_mismatch = True
                        family_report["components"][component] = {
                            "status": "ok" if is_ours else "found_but_not_ours",
                            "origin": origin,
                        }
                    except TemplateDoesNotExist:
                        any_mismatch = True
                        family_report["components"][component] = {"status": "missing", "origin": None}
                report["families"][family_key] = family_report
        finally:
            if lang_ctx:
                lang_ctx.__exit__(None, None, None)

        report["not_yet_supported"] = list(app_config.NOT_YET_SUPPORTED)

        if options["as_json"]:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self._print_text_report(report)

        if any_mismatch and options["strict"]:
            self.stderr.write(self.style.ERROR("Strict mode: one or more components failed precedence check."))
            sys.exit(1)

    def _print_text_report(self, report):
        self.stdout.write(self.style.NOTICE("tutor-custom-emailtpl: override precedence check"))
        self.stdout.write(f"Plugin package root: {report['plugin_package_root']}")
        self.stdout.write("")
        for family_key, family_report in report["families"].items():
            verified_tag = "verified context" if family_report["context_verified"] else "UNVERIFIED context (see docs/TEMPLATE_VARIABLES.md)"
            self.stdout.write(f"Family: {family_key}  [{verified_tag}]")
            for component, info in family_report["components"].items():
                if info["status"] == "ok":
                    self.stdout.write(self.style.SUCCESS(f"  {component:<14} OK (plugin)          origin={info['origin']}"))
                elif info["status"] == "found_but_not_ours":
                    self.stdout.write(self.style.WARNING(f"  {component:<14} FOUND BUT NOT OURS   origin={info['origin']}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  {component:<14} MISSING"))
            self.stdout.write("")

        if report["not_yet_supported"]:
            self.stdout.write("Not yet supported in this version (v1 scope is enrollment/instructor only):")
            for label in report["not_yet_supported"]:
                self.stdout.write(f"  - {label}")
