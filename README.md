# GoalTracker

GoalTracker is a small Flask application to organize and track interview preparation (goals, skills, daily tasks, and courses).

This README documents the current app behavior, configuration, and how to run it locally.

## Key features (current)
- User registration, login, and per-user data isolation.
- Interview goals with company, role, job description, notes, and status.
- Skill tracking per goal, including name, confidence level, status, notes, and resource link.
- Inline editing on the global `Skills` page: edit name, confidence, status, and notes directly from the list.
- Add new skills from the `Skills` page and assign them to a goal.
- Daily tasks board with recurrence support and quick toggle/delete controls.
- "Send summary" action on the daily page that emails a plaintext summary of today's tasks to the signed-in user (requires SMTP config).
- Dashboard with compact, server-side progress bars (chart canvases removed in current UI).
- Simple activity feed and compact goal/task/course overviews.

## Important routes (examples)
- `GET /` — Dashboard (requires login)
- `GET /daily` — Daily tasks board (add/toggle/delete tasks, Send summary button)
- `POST /daily/send-summary` — Send today's summary to the current user's email
- `GET /skills` — Global skills list (inline edit + add skills)
- `POST /skills/new` — Create a new skill from the skills page
- `POST /skills/<id>/update` — Inline skill update endpoint (AJAX)
- `GET /goals` and `GET /goals/<id>` — Manage interview goals

Search the `goaltracker` package for route names if you need to extend or link to other pages.

## Configuration
The minimal config values the app reads (set as environment variables or in-app config):

- `SECRET_KEY` — Flask secret key (default in development is `dev-secret-key-change-me`).
- `SQLALCHEMY_DATABASE_URI` — Database URI (default: SQLite file configured in app factory).

SMTP email settings (optional, required to use the "Send summary" feature):
- `MAIL_SERVER` (e.g. `smtp.gmail.com`)
- `MAIL_PORT` (e.g. `587`)
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_USE_TLS` (True/False, default True)
- `MAIL_USE_SSL` (True/False, default False)
- `MAIL_DEFAULT_SENDER` (optional)

If `MAIL_SERVER` is not set, the send-summary action will flash an error indicating mail isn't configured.

## Run locally
1. Create and activate a virtual environment (recommended).

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database (if using migrations):

```bash
flask --app run.py db upgrade
```

4. Seed the demo data (optional):

```bash
flask --app run.py seed-demo
```

5. Start the app:

```bash
python run.py
```

Open http://localhost:5000/ and sign in.

## Demo account
The project includes a seed command that creates a demo user and sample goals. After running `seed-demo`, use the demo credentials printed by the seeder (or inspect the seed file).

## Notes and caveats
- CSRF: If you enable CSRF protection (Flask-WTF or similar), ensure forms and AJAX calls include the token. The inline skill updates use a JSON POST endpoint — you may need to add the CSRF header to AJAX requests.
- Email: The current email helper uses Python's smtplib and the `MAIL_*` config described above. For production or richer features consider integrating a transactional email service or Flask-Mail.
- Charts: The previous canvas-based charts were removed; the dashboard uses compact server-rendered progress bars instead (no Chart.js dependency by default).

## Development tips
- Use `python -m compileall .` to quickly check for Python syntax errors after edits.
- Tests: There are no automated tests included. Adding unit tests for routes and utilities is recommended.

## Contributing
- Fork, branch, and open a pull request. Keep changes small and include a brief test/verification step in your PR description.

If you'd like, I can also:
- Add an HTML email template and wire the send-summary feature to send a nicer email.
- Add background job support for sending emails (RQ/Celery) so requests are non-blocking.
- Re-introduce optional charts behind a feature flag if you want visuals back.

---
Generated on behalf of the repository state (June 2026).
