#!/usr/bin/env python3
import os
import sys
from alembic.config import Config
from alembic import command

# ensure project root is on sys.path so 'goaltracker' package can be imported
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import app factory
try:
    from goaltracker import create_app
except Exception as e:
    print('Unable to import app factory:', e, file=sys.stderr)
    sys.exit(1)

base = os.path.dirname(__file__)
migrations_dir = os.path.abspath(os.path.join(base, '..', 'migrations'))
if not os.path.isdir(migrations_dir):
    print(f"migrations directory not found at {migrations_dir}", file=sys.stderr)
    sys.exit(1)

app = create_app()
with app.app_context():
    # build a Config programmatically
    cfg = Config()
    cfg.set_main_option('script_location', migrations_dir)
    # use DATABASE_URL env if set, otherwise app config, otherwise default sqlite
    db_url = os.environ.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI')
    if not db_url:
        default_db = os.path.abspath(os.path.join(base, '..', 'instance', 'goaltracker.db'))
        db_url = f"sqlite:///{default_db}"
    cfg.set_main_option('sqlalchemy.url', db_url)

    try:
        # upgrade all heads if multiple head revisions exist
        command.upgrade(cfg, 'heads')
        print('Migrations applied')
    except Exception as e:
        print('Migration failed:', e, file=sys.stderr)
        sys.exit(1)
