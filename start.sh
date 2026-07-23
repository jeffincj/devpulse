#!/bin/sh
python manage.py migrate
exec gunicorn devpulse_project.wsgi:application --bind 0.0.0.0:$PORT