import click

from sqlalchemy import inspect, text
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

try:
    from flask_migrate import Migrate
except ImportError:  # pragma: no cover - keeps the app importable before deps are installed
    class Migrate:  # type: ignore[no-redef]
        def init_app(self, app, db):
            return None

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message_category = "warning"


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///goaltracker.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    # register a context processor to adjust flashed messages wording
    @app.context_processor
    def _replace_project_in_flashes():
        from flask import get_flashed_messages as _orig_get_flashed
        def _get_flashed_messages(with_categories=False, category_filter=None):
            msgs = _orig_get_flashed(with_categories=with_categories, category_filter=category_filter)
            if with_categories:
                return [(cat, (msg.replace('project', 'goal') if isinstance(msg, str) else msg)) for cat, msg in msgs]
            return [(m.replace('project', 'goal') if isinstance(m, str) else m) for m in msgs]
        return dict(get_flashed_messages=_get_flashed_messages)

    # expose helper to templates: course_progress
    @app.template_global()
    def course_progress(course):
        """Return completion percentage for a course (0-100)."""
        try:
            total = int(getattr(course, 'total_lessons', 0) or 0)
            completed = int(getattr(course, 'completed_lessons', 0) or 0)
            if total <= 0:
                return 0
            return int(round((completed / total) * 100))
        except Exception:
            return 0

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()
        _ensure_daily_task_recurrence_columns()
        _ensure_chapter_completion_column()
        _ensure_goal_task_progress_column()

    from .seed import seed_demo_data

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Seed a demo user with sample interview goals."""
        seed_demo_data()
        click.echo("Seeded demo account and sample interview goals.")

    return app


def _ensure_daily_task_recurrence_columns():
    """Backfill recurrence columns for existing SQLite databases."""
    inspector = inspect(db.engine)
    if "daily_task" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("daily_task")}
    columns = {
        "recurrence_type": "VARCHAR(20) NOT NULL DEFAULT 'none'",
        "recurrence_interval_days": "INTEGER NOT NULL DEFAULT 1",
        "recurrence_days_of_week": "VARCHAR(50) NOT NULL DEFAULT ''",
        "recurring": "BOOLEAN NOT NULL DEFAULT 0",
    }
    with db.engine.begin() as connection:
        for name, ddl in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE daily_task ADD COLUMN {name} {ddl}"))


def _ensure_chapter_completion_column():
    """Backfill chapter completion for existing SQLite databases."""
    inspector = inspect(db.engine)
    if "chapter" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("chapter")}
    if "completed" in existing:
        return

    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE chapter ADD COLUMN completed BOOLEAN NOT NULL DEFAULT 0"))


def _ensure_goal_task_progress_column():
    """Backfill task progress for existing SQLite databases."""
    inspector = inspect(db.engine)
    if "goal_task" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("goal_task")}
    if "progress" in existing:
        return

    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE goal_task ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"))
