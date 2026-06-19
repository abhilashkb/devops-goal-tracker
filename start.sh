#!/bin/sh
# Apply database migrations
flask db upgrade

# Start the application
exec gunicorn -w 4 -b 0.0.0.0:5000 run:app