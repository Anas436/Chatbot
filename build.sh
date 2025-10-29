#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
if [[ $CREATE_SUPERUSER ]];
then
  python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi

# Start Command
# python manage.py migrate && python manage.py collectstatic && gunicorn django_chatbot.wsgi:application

#This file will be use in Render. During this project deployment on the cloud.
