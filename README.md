# Til

Russian–Uzbek learning platform, currently an early development prototype. The product plan is in [project/plan.md](project/plan.md).

- `app/frontend` — React, TypeScript and Vite interface.
- `app/backend` — FastAPI application, account sessions, onboarding preferences, exercise checking, saved progress and private post-lesson feedback.
- `materials` — original reference PDFs, grouped into vocabulary and reference guides.
- `project` — product plan and editorial working documents.

## Run locally

Requirements: Python 3.10+, Node.js 20.19+ or 22.12+, and PostgreSQL 16+.

Start PostgreSQL and create the development database and user, or run `docker compose -f app/compose.yaml up -d db` if Docker is available. The local development connection defaults to `postgresql+psycopg://til:til_dev_password@localhost:5432/til`; use `DATABASE_URL` to override it. Never use these development credentials in production.

```bash
python3 -m venv .venv
.venv/bin/pip install -r app/backend/requirements.txt
(cd app/backend && ../../.venv/bin/alembic upgrade head)
(cd app/backend && ENABLE_DEMO_CONTENT=true ../../.venv/bin/uvicorn app.main:app --reload)
```

In a second terminal:

```bash
cd app/frontend
npm install
npm run dev
```

The command above enables 118 additional unreviewed sample lessons (59 per direction) for the local MVP demonstration. Omit `ENABLE_DEMO_CONTENT=true` to disable them.

Open the local address printed by Vite. Vite forwards API requests to FastAPI on port 8000 by default; set `TIL_API_TARGET` when the API uses another local port. The application uses PostgreSQL; SQLite is used only by isolated tests. Set `WEB_ORIGIN` to the exact frontend origin if different from `http://127.0.0.1:5173`.

After completing setup, `./app/run-demo.sh` starts both local servers together and stops them with Ctrl+C. It applies pending migrations, checks that its ports are free, waits for the API database-readiness check, and binds only to this computer. PostgreSQL must already be running. Use `TIL_API_PORT` and `TIL_WEB_PORT` to select other ports, and `DATABASE_URL` for a non-default database. It will not stop servers already using those ports.

For a single-address local demo without the Vite development server, build the frontend once and run:

```bash
(cd app/frontend && npm run build)
./app/run-built-demo.sh
```

Open the printed `http://127.0.0.1:8000` address. Set `TIL_DEMO_PORT` for another port. This serves the built frontend from FastAPI and applies pending migrations; PostgreSQL must already be running. Rebuild after frontend changes. Both launchers bind to this computer only and are development/demo tools, not a public deployment setup.

The API exposes `/api/health` for process liveness and `/api/ready` for database connectivity; readiness returns HTTP 503 if its database query fails. These checks do not establish that the curriculum or deployment is ready for public use.

Frontend fonts are bundled locally; a running frontend and API do not require Google Fonts. Initial dependency installation still requires the configured package registries.

Practice assessments include a version token so changed questions are not silently graded against a different version. Saved scores are marked when questions have changed; scores created before version tracking are marked as unknown rather than assumed current. By default, an API restart requires an open practice assessment to reload. If multiple API workers are used, configure the same strong, private `PRACTICE_REVISION_KEY` for every worker; this development setting does not replace a production deployment review.

An older database used the same category for the greeting checkpoint and module 3 practice. The separation migration retains those ambiguous scores in the database but excludes them from both displays; new scores appear in their correct histories. Back up the database before migrating if those historical records need investigation.

## Current limitations

This is **not ready for public launch**. It contains two original, unreviewed demonstration lessons by default; the local demo option adds 118 more unreviewed samples, covering the planned lesson positions in both tracks. The complete reviewed curriculum, reliable licensed recordings, production deployment, and the plan's remaining safeguards and assessments are not yet in place. Do not use real learner data or publish source-derived content before the editorial, legal, privacy and security work described in the plan is complete.

## Draft editor

After registering an account, an operator can grant it editor access from `app/backend`:

```bash
../../.venv/bin/python -m scripts.grant_editor editor@example.com
```

Sign in again or refresh to open the editor and the dashboard feedback inbox. Editors can create and update private drafts with vocabulary and exercises, inspect revision history, load an earlier revision into the form, and preview the current form locally. Stale saves are rejected. Validation checks answer options and unique exercise IDs. A different editor can record an approval or request changes for a specific saved revision. These records do not verify reviewer qualifications. An operator can grant a separate publisher permission with `../../.venv/bin/python -m scripts.grant_publisher editor@example.com`. A publisher can publish the saved revision only after independent approval and rights approval for audio on every vocabulary item and any attached exercise audio. Attempts and queued reviews retain their original content snapshot. Publishers can withdraw a lesson from the catalog with a reason; learners with an existing attempt can still resume it. Audio remains available to those learners only while its rights approval remains valid. For a published draft lesson, a publisher can instead apply a safety block with a reason: the lesson leaves the catalog and its attempts, results and review items are unavailable until the block is lifted. Lifting it restores existing attempts but does not republish the lesson. Audio referenced only by blocked lessons is unavailable; revoke the asset’s rights separately when the audio itself must be stopped across all lessons. The two built-in demonstration lessons are not covered by this publisher control. This is a development workflow and does not replace professional review or legal clearance.

Guest visitors can submit anonymous feedback from the trial exercise; registered learners can leave feedback from a lesson. A 1–5 clarity rating and a written comment are each optional, but at least one is required. Reports appear in the editor’s private Feedback inbox. Ask visitors not to include personal information in anonymous reports. To read open reports directly as a local operator, run `(cd app/backend && ../../.venv/bin/python -m scripts.list_feedback)`. Use `--status all` to include resolved reports. This command is read-only and omits account identifiers; the editor inbox can change report status. Reports may contain free text, so share them only with people responsible for review.

Lesson vocabulary can use an available browser voice in the target language when no recorded audio is attached. This speech is computer-generated, depends on the visitor’s device, and is not a substitute for reviewed recordings or listening assessments.

## Local database backup

With PostgreSQL client tools installed, the operator can create a new private archive without overwriting an existing file:

```bash
cd app/backend
../../.venv/bin/python -m scripts.backup_database /secure/path/til-backup.dump
```

Set `DATABASE_URL` to select the database. The tool runs `pg_dump` and checks that `pg_restore --list` can read the archive. This is not a restore test. The database archive can contain private account data; store it securely and define retention and deletion procedures. It does **not** include uploaded files under `MEDIA_ROOT` (default `app/backend/.media/`), which must be backed up separately and kept consistent with the database. Test restoring both database and media into an isolated environment before relying on a backup. Do not restore over a live database. A repeatable database-only restore smoke test uses the dedicated, idle `til_test` database as its source and creates a temporary PostgreSQL cluster owned by the current user:

```bash
cd app/backend
DATABASE_URL=postgresql+psycopg://til:til_dev_password@localhost:5432/til_test \
  ../../.venv/bin/python -m tests.postgres_backup_restore_smoke
```

The check restores the archive and compares the migration version and selected table row counts. It requires PostgreSQL server tools and does not verify uploaded media or every record.

To test an existing archive, without connecting to or overwriting any existing database, run as an unprivileged user with PostgreSQL server and client tools installed:

```bash
cd app/backend
../../.venv/bin/python -m scripts.verify_database_backup /secure/path/til-backup.dump
```

This restores into a private temporary PostgreSQL cluster with no TCP listener, checks that a migration version exists, and removes the temporary cluster afterward. It does not compare every record or verify media files. The temporary directory must have enough free space for the restored data.

## Password-reset email

Set `SMTP_HOST` and `SMTP_FROM` for reset emails. Optional settings are `SMTP_PORT` (default `587`), `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_STARTTLS` (default `true`). Set `WEB_ORIGIN` to the exact frontend origin; reset links use it. Without SMTP configuration, the recovery screen explains that email recovery is unavailable. Direct API requests retain the same neutral response for known and unknown accounts and deliver no email. The flow needs production rate limiting, delivery monitoring and HTTPS before public use.

## Account deletion requests

Learners can submit a deletion request from their profile. From `app/backend`, an operator can list pending requests with `../../.venv/bin/python -m scripts.list_deletion_requests`, then preview an eligible request with `../../.venv/bin/python -m scripts.fulfill_deletion USER_ID`. The same command with `--execute` permanently deletes the eligible account and its associated learner data in one transaction and returns a non-identifying receipt. Only a pending request can be fulfilled. Accounts with editorial access or shared editorial references are refused and require manual dependency handling; no shared content is deleted automatically.

The command does not notify the learner or remove data from backups, external logs, mail systems, or shared rate-limit buckets. Backup expiration, external data handling, notification, identity verification and a retention policy still require an operational process before launch.

## Database migrations

Alembic manages the schema; run `../../.venv/bin/alembic upgrade head` from `app/backend` before starting the API. The initial revision is intended for a **new, empty** database. Existing databases created by earlier prototype versions need a backup and a schema comparison before any migration or baseline stamp; do not blindly stamp an unverified schema. The migration and a concurrent lesson smoke test have been verified on fresh local PostgreSQL databases; broader integration and production testing remain necessary.

## Request limits

The API applies database-backed fixed-window limits to registration, login, password reset and lesson answers. It uses the direct connection address and does not trust forwarded headers. When a proxy obscures client addresses, configure trusted client-address handling and an edge limiter before deployment; otherwise users may share one limit. This is one safeguard, not a substitute for a production security review.

## Draft audio

Editors can upload audio up to 5 MB and attach it to vocabulary or listening exercises in a draft. Files are stored in the private local `app/backend/.media/` directory by default, or under `MEDIA_ROOT` if configured, and require editor authentication to retrieve. Upload checks identify common file signatures but do not validate audio integrity, quality or rights. Assets start unverified; an independent editor can record a rights review. Audio referenced by a published revision can be served to learners while its rights status remains approved. Local disk is a development implementation: use durable private object storage, media validation, rights review, and backups before deployment.

To run the PostgreSQL concurrency smoke test, use a dedicated migrated database named `til_test`, then from `app/backend` run `DATABASE_URL=postgresql+psycopg://til:til_dev_password@localhost:5432/til_test ../../.venv/bin/python -m tests.postgres_smoke`. The script creates a uniquely named test account and does not delete existing records.

Publication and pinned attempts are also covered by `tests.postgres_publication_smoke` against the dedicated `til_test` database. Both PostgreSQL smoke tests create uniquely named test records and leave them in that test database. Sample module and course practice, progress access, and guest feedback can be checked with `ENABLE_DEMO_CONTENT=true DATABASE_URL=postgresql+psycopg://til:til_dev_password@localhost:5432/til_test ../../.venv/bin/python -m tests.postgres_practice_smoke`. It also creates test records only in `til_test`.

## Vocabulary staging

The internal, unreviewed heading inventory is under `project/staging/`; see its README and `project/docs/editorial/vocabulary-extraction-assessment.md`. Editors can search a read-only source view and append private assessments with proposed classification and review notes tied to each source hash. Assessments do not alter source records, establish rights, or publish content. Set `STAGED_VOCABULARY` if the staging JSONL is stored outside the default project path. Run its checks from the repository root with `python3 -m unittest discover -s project/tools -p 'test_*.py'`.

## Curriculum planning

`project/curriculum/` contains 60 unreviewed lesson outlines for each direction, accessible to editors as planning material. Editors can start an unsaved draft from an outline; its source hash and position are recorded with the draft. The outline view links related drafts and shows review, publication, and source-change indicators. The outlines are not playable lessons or a validated CEFR assessment. Set `CURRICULUM_ROOT` if these files are deployed outside the default project path. Educator review, original lesson authoring, recordings and assessments remain required.

Draft exercises can specify case sensitivity, tolerance for trailing sentence punctuation, and acceptance of Uzbek apostrophe variants. The backend applies the policy stored in the lesson snapshot; `е` and `ё`, and letters with and without the Uzbek apostrophe, remain distinct. The editor's in-browser preview is approximate; server checking is authoritative.

The editor supports typed responses, single choice, word order, listening, guided dialogue and matching exercises. Matching pairs are shuffled independently for the learner and checked on the server; their pairings are not sent with the exercise before an answer is submitted.

The learner progress view counts completion of currently available lesson revisions and due review items; it is not a language-level or mastery assessment. A new published revision requires a new completion, while republishing the same draft version retains credit.

During a lesson, missed exercises are revisited before completion. The recorded score remains based on first answers; a successful in-session retry schedules the mistake for later review. Existing unfinished attempts are backfilled during the remediation migration.

## Browser smoke test

The browser smoke test creates a new learner and lesson attempt. Run it only against a disposable, isolated test database, never against the development database containing real demo feedback or learner progress. For example, with Chrome installed at `/opt/google/chrome/chrome`:

```bash
# Terminal 1: create/migrate the disposable SQLite database and start separate local ports.
DATABASE_URL=sqlite:////tmp/til-e2e.db TIL_API_PORT=8012 TIL_WEB_PORT=5174 ./app/run-demo.sh

# Terminal 2: from the project root, point the test at that isolated instance.
cd app/frontend
TIL_E2E_ISOLATED=1 TIL_E2E_BASE_URL=http://127.0.0.1:5174/ \
  TIL_BROWSER_PATH=/opt/google/chrome/chrome npm run test:e2e
```

The test covers signup, onboarding, completing a question, resuming the numbers lesson, typed and matching exercises, and completion. Repeat with `npm run test:e2e:ru` under the same environment variables to check the Russian-interface / Uzbek-learning direction. SQLite here is for this isolated smoke test; PostgreSQL remains the application database. The browser executable must be installed separately.

A limited automated accessibility smoke check covers the Uzbek home and guest-preview screens at a mobile viewport. It does not create an account or replace manual accessibility review:

```bash
cd app/frontend
TIL_E2E_BASE_URL=http://127.0.0.1:5173/ TIL_BROWSER_PATH=/opt/google/chrome/chrome npm run test:a11y
```

The signed-in accessibility smoke check creates a test account and must use the disposable test instance described above:

```bash
TIL_E2E_ISOLATED=1 TIL_E2E_BASE_URL=http://127.0.0.1:5174/ \
  TIL_BROWSER_PATH=/opt/google/chrome/chrome npm run test:a11y:learner
```

It covers the Uzbek dashboard, a sample lesson introduction, and one exercise at a mobile viewport. Other screens, languages, assistive technologies and manual keyboard review remain to be checked.

The listening smoke check also uses the disposable test instance and simulates a browser voice; it does not evaluate actual audio quality:

```bash
TIL_E2E_ISOLATED=1 TIL_E2E_BASE_URL=http://127.0.0.1:5174/ \
  TIL_BROWSER_PATH=/opt/google/chrome/chrome npm run test:listening
```

## Hosting preparation

`netlify.toml` builds the frontend with `TIL_API_ORIGIN` set to the public HTTPS origin of a separately deployed FastAPI backend. Its `/api/*` proxy preserves same-origin browser requests. `render.yaml` is a starting configuration for a free Render API and PostgreSQL database; set `WEB_ORIGIN` to the exact Netlify site origin before launch. Render's free database expires after 30 days, and free service storage is ephemeral, including uploaded media. Configure durable storage, backups, security settings, and a reviewed content and privacy process before relying on a public installation. Create a separate cloud database: do not copy local user data automatically.
