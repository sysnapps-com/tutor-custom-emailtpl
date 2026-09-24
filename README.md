# tutor-custom-emailtpl (v1.1)

A Tutor plugin + companion Django app that lets an Open edX administrator
customize a subset of ACE-driven email templates without editing
`edx-platform` source or the Docker image, and without losing the
customization on upgrade.

Repository: https://github.com/sysnapps-com/tutor-custom-emailtpl

## v1.1 scope: Enrollment and instructor operations ONLY

This version implements exactly these 8 ACE message families and nothing
else:

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

### Not yet supported (explicitly out of scope for v1.1)

Accounts/Authentication, Course communication/Schedules, Discussions,
Notifications, Certificates, Bulk email, Commerce/Subscriptions. The
architecture generalizes to these without a redesign -- see "Extending to
the next category" below.

## Verified template variables

See **[`docs/TEMPLATE_VARIABLES.md`](docs/TEMPLATE_VARIABLES.md)** for
the full, cited breakdown. Summary:

- `instructor:accountcreationandenrollment`: `course_name`, `site_name`
  (a bare domain, e.g. `example.tld`, not a friendly platform name),
  `email_address`, `password`, `course_url` -- confirmed both by direct
  inspection of edx-platform's own packaged template and by live testing
  on a Verawood instance.
- The other 6 `instructor:*` families share the same underlying
  `param_dict`-building code path and are treated as using `course_name`
  too, on that strength. No `password` variable for these 6 -- they act
  on accounts that already exist.
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
   typed into a database field), so the model has a `language` column:
   one row per `(family_key, language)` pair. **This registry is not
   wired into the actual render path** in v1.1 (see "Customizing your own
   templates" below) -- it remains scaffolding for a future release that
   adds a small ACE message override.

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
  of the release name's first letter (Aspen->1 ... Ulmo, the 21st letter
  -> 21, Verawood, the 22nd -> 22), which matches Tutor v22.0.0 shipping
  Verawood support. Ulmo therefore corresponds to **Tutor v21.x**.
- What is *not* independently re-verified here: that the `ENV_PATCHES`
  patch names this plugin uses (`openedx-dockerfile-post-python-
  requirements`, `openedx-common-settings`) are unchanged between Tutor
  v21 and v22. These are long-standing, stable Tutor hook names with no
  deprecation notice found in the Verawood/Tutor v22 release notes
  reviewed, but that is inference, not a running-instance confirmation.

To install against Ulmo, pin Tutor to the matching range instead of
letting this package's default range resolve:

```bash
pip install "tutor>=21.0.0,<22.0.0"
pip install --no-deps tutor-custom-emailtpl
```

Run `check_email_templates` after `tutor images build` either way -- it
is release-agnostic and is exactly how you confirm precedence actually
took effect on whichever release you're running.

## Installation

### Option A: install from PyPI (if published)

```bash
pip install tutor-custom-emailtpl
tutor plugins enable emailtpl
tutor config save
tutor images build openedx
tutor local launch
```

### Option B: install directly from GitHub

```bash
pip install "git+https://github.com/sysnapps-com/tutor-custom-emailtpl.git"
tutor plugins enable emailtpl
tutor config save
tutor images build openedx
tutor local launch
```

To pin a specific tag, release, or branch instead of the default branch,
append a `@` ref:

```bash
pip install "git+https://github.com/sysnapps-com/tutor-custom-emailtpl.git@v1.1"
```

If you're developing locally against a clone rather than installing from
GitHub directly:

```bash
git clone https://github.com/sysnapps-com/tutor-custom-emailtpl.git
pip install -e ./tutor-custom-emailtpl
tutor plugins enable emailtpl
tutor config save
```

An editable install (`-e`) means changes to your local clone -- including
to the packaged template files under
`tutor_custom_emailtpl/emailtpl_app/templates/` -- take effect the next
time you rebuild the openedx image, with no need to reinstall the Python
package itself.

### Updating to a newer version

**If you installed from PyPI:**

```bash
pip install --upgrade tutor-custom-emailtpl
tutor config save
tutor images build openedx
tutor local launch
```

**If you installed from GitHub:**

```bash
pip install --upgrade --force-reinstall "git+https://github.com/sysnapps-com/tutor-custom-emailtpl.git"
tutor config save
tutor images build openedx
tutor local launch
```

`pip install --upgrade` alone is not always reliable for a `git+https://`
source pointed at a moving branch (pip may decide the requirement is
already "satisfied" and skip re-fetching) -- `--force-reinstall` makes
sure the latest commit is actually pulled. If you pinned a tag
(`@v1.1`), change the tag in the URL to the new one you want instead.

**If you installed as an editable clone:**

```bash
cd tutor-custom-emailtpl
git pull
tutor config save
tutor images build openedx
tutor local launch
```

**In every case**, `tutor images build openedx` is required after an
update -- this is what actually copies the (new) package into the LMS/CMS
image; `pip install --upgrade` on its own only updates the package in
your local/host Python environment, not inside the built image. Run
`check_email_templates` (see "Verifying overrides took effect" below)
after rebuilding to confirm the new templates actually took precedence.

## Configuration keys

| Key | Default | Meaning |
|---|---|---|
| `EMAILTPL_ENABLED` | `true` | Master on/off switch for the settings patch. |
| `EMAILTPL_FAIL_OPEN_TO_UPSTREAM` | `true` | Governs the plugin's own defensive template lookups; does not affect Django's own loader fallback behavior. |
| `EMAILTPL_INSTALL_SOURCE` | `pypi` | How the Dockerfile patch installs this package into the image: `pypi` (default, `pip install tutor-custom-emailtpl`), `none` (skip the patch -- wire up your own install step, e.g. for a local mount during development), or any other string, used verbatim as a pip requirement spec. To match a GitHub install, set this to `git+https://github.com/sysnapps-com/tutor-custom-emailtpl.git` (optionally with an `@ref`) so the *image build* installs from the same place you did on the host. |
| `EMAILTPL_SUPPORTED_LANGUAGES` | `["en"]` | Informational only -- documents which languages an operator has actually checked with `check_email_templates --language`. Not enforced anywhere; Django will render in any language with an installed catalog regardless of this list. |

## Customizing your own templates

There are two ways to change what these emails say, depending on how much
you want to change and how you prefer to work.

### Option 1: edit the packaged template files directly (recommended for v1.1)

This is the only method that's actually wired into the render path today
(see "Option 2" below for why the database-registry approach isn't yet).

1. Get a local copy of the plugin source, either freshly cloned or
   already installed editable (see "Option B" installs above):

   ```bash
   git clone https://github.com/sysnapps-com/tutor-custom-emailtpl.git
   cd tutor-custom-emailtpl
   ```

2. Find the family you want to change under:

   ```
   tutor_custom_emailtpl/emailtpl_app/templates/<family-path>/email/
   ```

   using the "Family key" -> "Upstream template path" table at the top of
   this README to find `<family-path>` (e.g.
   `instructor/edx_ace/allowedenroll/email/`).

3. Each family has 5 files -- edit whichever you need:

   | File | Purpose | Format |
   |---|---|---|
   | `subject.txt` | Email subject line | plain text, single line |
   | `from_name.txt` | Display name in the "From" field | plain text, single line |
   | `body.txt` | Plaintext email body | plain text |
   | `body.html` | HTML email body | HTML |
   | `head.html` | Extra `<head>` content for the HTML version | HTML (usually left minimal) |

   Both `body.txt` and `body.html` must be present and non-empty for a
   given family -- this plugin's registry model enforces "no HTML-only
   overrides" at the database level, and as a matter of email
   deliverability/accessibility you should keep that guarantee here too
   even though nothing mechanically stops you from leaving `body.txt`
   sparse.

4. Use `{% load i18n %}` and wrap literal text in `{% blocktrans trimmed %}
   ...{% endblocktrans %}` (as the shipped templates already do) rather
   than plain `{{ variable }}` interpolation outside a translation tag --
   this is what lets the same file render correctly for learners in any
   language your site has a catalog for. See "Multi-language behavior"
   above.

5. Only use variables listed in
   [`docs/TEMPLATE_VARIABLES.md`](docs/TEMPLATE_VARIABLES.md) for the
   family you're editing -- an unlisted variable name doesn't error, it
   silently renders as blank (Django's default behavior for an undefined
   template variable). If you reference a variable and it comes out
   empty in a real test send, check the variable name against that doc
   first.

6. If you add a value that might contain special characters (a
   generated password, for example) to a `.txt` component, wrap it in
   `{% autoescape off %}` / `{% endautoescape %}` -- see the "plaintext
   escaping" note in `docs/TEMPLATE_VARIABLES.md` for why this matters
   and what goes wrong if you skip it.

7. Rebuild and relaunch:

   ```bash
   tutor images build openedx
   tutor local launch
   ```

8. Confirm your edit actually took effect and rendered without error:

   ```bash
   python manage.py lms check_email_templates --family <family-key>
   ```

   (Run this inside the LMS container, e.g. via `tutor local exec lms
   ...` if you're not already inside it.) A `MISSING` result or a
   `TemplateDoesNotExist`-style failure here means a typo in the file
   path or a Django template syntax error, not a variable problem.

9. Commit your change and push it to your own fork/branch (or your copy
   of this repository) so `EMAILTPL_INSTALL_SOURCE` can point at it for
   every environment, rather than keeping a one-off local edit that gets
   lost on the next clean install. See "Updating to a newer version"
   above once your own template edits are just another commit to pull.

### Option 2: the `EmailFamilyOverride` registry model (scaffolding, not yet live)

`emailtpl_app.models.EmailFamilyOverride` is a minimal per-language
database model an admin could populate (via Django admin or a data
migration) to override subject/body/from-name per family without editing
template files at all. It reserves `organization_slug` and `course_key`
fields for future per-org/per-course selection, and a `language` column
for per-locale content.

**v1.1 does not wire this registry into the actual render path** -- that
requires a corresponding change inside edx-platform's `enrollment.py` /
ACE message classes, which this plugin does not vendor or patch, since
its scope is template overrides via Tutor patches only. Populating this
model today has no visible effect on sent emails; it's scaffolding for a
future release. Use Option 1 above for anything you need working now.

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
`celery` isn't installed -- add the `dev` extra to include it); the
legacy CSV auto-register/auto-enroll welcome email specifically renders
and sends with a working generated password.

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
6. **The other 6 `instructor:*` families' `course_name` variable** --
   confirmed by strong analogy to `accountcreationandenrollment`, not
   individually source-inspected. See `docs/TEMPLATE_VARIABLES.md`.

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
   `docs/TEMPLATE_VARIABLES.md` before shipping sample copy for it --
   prefer direct template/source inspection or live-instance testing over
   docstring prose alone.
5. No change is needed to the Tutor-side settings patch.
