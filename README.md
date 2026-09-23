# tutor-custom-emailtpl (v1.1)


A Tutor plugin + companion Django app that lets an Open edX administrator
customize a subset of ACE-driven email templates without editing
`edx-platform` source or the Docker image, and without losing the
customization on upgrade.

## What's new in v1.1

- **Renamed** `tutor-contrib-emailoverrides` → `tutor-custom-emailtpl` *Formerly `tutor-contrib-emailoverrides`. Renamed -- see "Renamed from v1" below if you have the old package installed.*
  (package, Tutor plugin name, Django app, config keys, management
  command). See "Renamed from v1" below.
- **Verified template variables.** The previous version's context
  variables (`course_name`, `platform_name`) were unverified placeholders
  and were wrong. They're replaced with `display_name` and `site_name`,
  confirmed against edx-platform's own docstrings -- see
  [`docs/TEMPLATE_VARIABLES.md`](docs/TEMPLATE_VARIABLES.md) for the full,
  cited list of which variables are verified vs. still inferred.
- **Multi-language support.** Packaged templates now use
  `{% load i18n %}` + `{% blocktrans %}` so one file renders correctly
  under any active learner language, same as upstream. The admin registry
  model gained a `language` column for per-locale custom copy. See
  "Multi-language behavior" below.
- **New flags** on `check_email_templates` (renamed from
  `check_email_overrides`): `--family`, `--language`, `--json`, in
  addition to the existing `--strict`.
- **Corrected `pyproject.toml`:** `tutor>=22.0.0,<23.0.0` (was wrongly
  pinned to `<19.0.0`; Tutor v22 is the release that added Verawood
  support), Python floor raised to `>=3.10` (Tutor v22 itself requires
  3.10+), and a `dev` extra for test-only dependencies.
- **MIT license added** (`LICENSE`), replacing the earlier unstated
  license. Includes the standard "AS IS" warranty disclaimer.
- **Ulmo compatibility checked** -- see "Ulmo compatibility" below.

## Renamed from v1

If you have `tutor-contrib-emailoverrides` enabled from the previous
version:

```bash
tutor plugins disable emailoverrides
pip uninstall tutor-contrib-emailoverrides
pip install tutor-custom-emailtpl
tutor plugins enable emailtpl
tutor config save
```

The old `EMAILOVERRIDES_*` config keys are gone; their replacements are
`EMAILTPL_*` (see "Configuration keys" below). The old
`check_email_overrides` command is renamed `check_email_templates`. The
registry model's table name and app label changed
(`emailoverride_app` → `emailtpl_app`); if you had populated the old
`EmailFamilyOverride` table, re-enter that content after upgrading --
this version does not ship a data migration from the old table, since the
schema also gained a `language` column (see below) that has no equivalent
in the old data.

## v1 scope: Enrollment and instructor operations ONLY

Unchanged from v1 -- these 8 ACE message families and nothing else:

| Family key | Upstream template path |
|---|---|
| `instructor:accountcreationandenrollment` | `instructor/edx_ace/accountcreationandenrollment/email/*` |
| `instructor:allowedenroll` | `instructor/edx_ace/allowedenroll/email/*` |
| `instructor:allowedunenroll` | `instructor/edx_ace/allowedunenroll/email/*` |
| `instructor:enrollenrolled` | `instructor/edx_ace/enrollenrolled/email/*` |
| `instructor:enrolledunenroll` | `instructor/edx_ace/enrolledunenroll/email/*` |
| `instructor:addbetatester` | `instructor/edx_ace/addbetatester/email/*` |
| `instructor:removebetatester` | `instructor/edx_ace/removebetatester/email/*` |
| `support:wholecoursereset` | `support/edx_ace/wholecoursereset/email/*` |

Each family has 5 ACE components: `from_name.txt`, `subject.txt`,
`body.html`, `head.html`, `body.txt`.

### Not yet supported (explicitly out of scope for v1)

Accounts/Authentication, Course communication/Schedules, Discussions,
Notifications, Certificates, Bulk email, Commerce/Subscriptions. See
`docs/TEMPLATE_VARIABLES.md` and the v1 README history for why these are
deferred; the architecture generalizes to them without a redesign.

## Verified template variables (v1.2 correction)

See **[`docs/TEMPLATE_VARIABLES.md`](docs/TEMPLATE_VARIABLES.md)** for
the full, cited breakdown -- including a v1.1 -> v1.2 correction:
**the real variable is `course_name`, not `display_name`**, and
`instructor:accountcreationandenrollment` (the family behind the legacy
instructor-dashboard **CSV auto-register/auto-enroll** feature) does
carry a real **`password`** variable, confirmed both by direct
inspection of edx-platform's own packaged template and by live testing
on a Verawood instance. Summary:

- `instructor:accountcreationandenrollment`: `course_name`, `site_name`
  (a bare domain, not a friendly platform name), `email_address`,
  `password`, `course_url` -- empirically confirmed.
- The other 6 `instructor:*` families share the same underlying
  `param_dict`-building code path and are treated as using `course_name`
  too, on that strength (not each individually source-inspected). No
  `password` variable for these 6 -- they act on existing accounts.
- `support:wholecoursereset` has no equivalent documented `param_dict`;
  its `course_name`/`course_id`/`course_url`/`site_name` usage is
  inferred and flagged as **unverified** by `check_email_templates`.

## The legacy CSV auto-register/auto-enroll mechanism

`instructor:accountcreationandenrollment` is the family sent by the
instructor dashboard's Membership tab CSV-upload feature, which creates
new accounts, auto-enrolls them, and emails each a generated password.
It's **off by default** (Verawood included), behind the
`ALLOW_AUTOMATED_SIGNUPS` feature toggle -- see
[`docs/TEMPLATE_VARIABLES.md`](docs/TEMPLATE_VARIABLES.md) for the
toggle's exact type, source location, and how to enable it in Tutor. This
is useful when standard public self-registration is restricted (e.g. by a
`tutor-restricted-signups`-style plugin) and staff still need a way to
onboard learners who can't self-register.

`emailtpl_app/tests/test_overrides.py::CsvAutomatedSignupsWelcomeEmailTest`
specifically exercises this mechanism with the confirmed variable set
(including a password containing a special character, to catch escaping
bugs) and proves the rendered email contains a working password and
sends successfully.

## Multi-language behavior

Two independent mechanisms, don't confuse them:

1. **Packaged template files** (under `templates/`) are not duplicated
   per language. They use `{% load i18n %}` and `{% blocktrans %}` around
   every literal string, so Django's normal translation machinery
   (`.po`/`.mo` catalogs, `translation.override()` / ACE's own
   `language=` argument) picks the right rendering automatically, exactly
   like upstream edx-platform templates. There is nothing to configure
   for this to work beyond having a compiled catalog for the target
   language -- untranslated strings simply render in the source language.
2. **Admin-authored content** in the `EmailFamilyOverride` registry model
   cannot be auto-translated (Django can't translate free text an admin
   typed into a database field), so v1.1 adds a `language` column: one row
   per `(family_key, language)` pair. **This registry is still not wired
   into the actual render path** in v1.1 (see "Customizing content"
   below) -- it remains scaffolding for a future release that adds a
   small ACE message override.

`check_email_templates --language <code>` renders every in-scope
component with that language active as a structural smoke test (it does
not require a real catalog for `<code>` to exist -- it only proves the
`{% blocktrans %}` usage doesn't raise).

## Target releases

- **Primary target: Verawood.** `pyproject.toml` pins
  `tutor>=22.0.0,<23.0.0` -- Tutor v22.0.0 is the release that added
  Verawood support (`OPENEDX_COMMON_VERSION = release/verawood.1`) and
  also raised Tutor's own Python floor to 3.10, which is why this
  package's `requires-python` matches.

### Ulmo compatibility

**Checked, and the architecture holds, but the Tutor pin differs.**

- The reference inventory shows all 8 in-scope families present with
  identical component sets in both the Ulmo and Verawood columns -- no
  template paths changed between the two releases for this family set.
- `lms.djangoapps.support.message_types.WholeCourseReset` and the
  `instructor` message types / `enrollment.py` docstring contract used in
  `docs/TEMPLATE_VARIABLES.md` are both independently confirmed present
  on the **Ulmo** published docstring pages, not just Quince.
- Tutor's own versioning convention ties its major version to the ordinal
  of the release name's first letter (Aspen→1 ... Ulmo, the 21st letter →
  21, Verawood, the 22nd → 22), which matches Tutor v22.0.0 shipping
  Verawood support. Ulmo therefore corresponds to **Tutor v21.x**.
- What is *not* independently re-verified here: that the `ENV_PATCHES`
  patch names this plugin uses (`openedx-dockerfile-post-python-
  requirements`, `openedx-common-settings`) are unchanged between Tutor
  v21 and v22. These are long-standing, stable Tutor hook names with no
  deprecation notice found in the Verawood/Tutor v22 release notes
  reviewed, but that is inference, not a running-instance confirmation.

To install against Ulmo, override the Tutor pin at install time (do not
edit `pyproject.toml`'s upper bound blindly -- reinstall with an explicit
constraint instead so pip's resolver still sees the real published
range):

```bash
pip install "tutor>=21.0.0,<22.0.0" tutor-custom-emailtpl --no-deps
pip install tutor-custom-emailtpl  # then let pip fill in the rest against the pinned tutor
```

or simpler, in a dedicated virtualenv already running Tutor v21:

```bash
pip install --no-deps tutor-custom-emailtpl
```

Run `check_email_templates` after `tutor images build` either way -- it
is release-agnostic and is exactly how you confirm precedence actually
took effect on whichever release you're running.

## Installation

```bash
pip install tutor-custom-emailtpl
tutor plugins enable emailtpl
tutor config save
tutor images build openedx
tutor local launch
```

## Configuration keys

| Key | Default | Meaning |
|---|---|---|
| `EMAILTPL_ENABLED` | `true` | Master on/off switch for the settings patch. |
| `EMAILTPL_FAIL_OPEN_TO_UPSTREAM` | `true` | Governs the plugin's own defensive template lookups; does not affect Django's own loader fallback behavior. |
| `EMAILTPL_INSTALL_SOURCE` | `pypi` | How the Dockerfile patch installs this package into the image: `pypi` (default, `pip install tutor-custom-emailtpl`), `none` (skip the patch -- wire up your own install step, e.g. for a local mount during development), or any other string, used verbatim as a pip requirement spec (a VCS URL, a private-index package name, etc). |
| `EMAILTPL_SUPPORTED_LANGUAGES` | `["en"]` | Informational only -- documents which languages an operator has actually checked with `check_email_templates --language`. Not enforced anywhere; Django will render in any language with an installed catalog regardless of this list. |

## Verifying overrides took effect

```bash
python manage.py lms check_email_templates
python manage.py lms check_email_templates --family instructor:allowedenroll --language es
python manage.py lms check_email_templates --json
python manage.py lms check_email_templates --strict   # exit non-zero on any mismatch, e.g. in CI
```

Output flags each family as `[verified context]` or `[UNVERIFIED
context]` per `docs/TEMPLATE_VARIABLES.md`, and reports per-component
`django.template.loader.get_template(...).origin` to confirm this
plugin's package actually won precedence.

## Customizing content

`emailtpl_app.models.EmailFamilyOverride` is a minimal per-language
registry model an admin can populate (via Django admin or a data
migration) to override subject/body/from-name per family without
touching the packaged template files. It reserves (but does not yet use)
`organization_slug` and `course_key` fields for future per-org/per-course
selection.

**v1.1 still does not wire this registry into the actual render path**
(that requires a corresponding change inside edx-platform's
`enrollment.py` / ACE message classes, which this plugin does not vendor
or patch). Today, "customization" happens by editing the packaged
template files directly (using the verified variables above and keeping
the `{% blocktrans %}` wrapping for i18n) and re-publishing the package.

## Tests

```bash
cd tutor_custom_emailtpl
python -m django test emailtpl_app --settings=emailtpl_app.tests.test_settings
```

Proves, for all 8 families: all 5 components render; no family is
HTML-only; every family renders under every language in `LANGUAGES`
without raising (a structural i18n smoke test, not a translation-
correctness test); a rendered family sends via Django's locmem backend;
the same path works under Celery's eager-execution mode (skipped if
`celery` isn't installed -- add the `dev` extra to include it).

## Open assumptions (validate before production use)

1. **Template name base.** This plugin's `DIRS` entry is prepended
   assuming `get_template()` is called with names relative to
   `lms/templates/` (e.g. `instructor/edx_ace/.../body.html`). Not
   independently confirmed against a captured `get_template()` call site.
   **Validate with `check_email_templates` on a real instance.**
2. **`support:wholecoursereset` context variables** -- see
   `docs/TEMPLATE_VARIABLES.md`; inferred, not confirmed.
3. **Multiple template engines.** The settings patch searches `TEMPLATES`
   for `BACKEND == "django.template.backends.django.DjangoTemplates"`
   rather than assuming index 0. Not exercised against a real
   `TEMPLATES` list in this exercise.
4. **Ulmo hook-name stability** -- see "Ulmo compatibility" above.
5. **Dockerfile install patch** assumes `EMAILTPL_INSTALL_SOURCE=pypi` is
   reachable from a package index at image-build time; use `none` or a
   custom spec otherwise (see "Configuration keys").

## License

MIT. See [`LICENSE`](LICENSE). The software is provided "AS IS", without
warranty of any kind, express or implied.

## Extending to the next category

To add another category (e.g. Notifications) later:

1. Add its families' upstream-relative paths as a new dict (mirroring
   `EmailTplAppConfig.SUPPORTED_FAMILIES`), kept distinguishable from the
   existing one so `check_email_templates` output stays legible.
2. Add matching `templates/<category>/edx_ace/<family>/email/*` files,
   using `{% load i18n %}` + `{% blocktrans %}` as the existing families
   do.
3. Add `FAMILY_CHOICES` entries to `EmailFamilyOverride` (no schema
   change needed for scope fields).
4. Verify and document that category's context variables in
   `docs/TEMPLATE_VARIABLES.md` before shipping sample copy for it.
5. No change is needed to the Tutor-side settings patch.
