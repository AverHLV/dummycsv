release: cd dummycsv && echo $CONFIG | base64 -d > ./config/config_deploy.ini && python manage.py migrate
web: cd dummycsv && echo $CONFIG | base64 -d > ./config/config_deploy.ini && python manage.py collectstatic --noinput && celery -A config worker -l INFO && gunicorn config.wsgi -b 0.0.0.0:$PORT --workers=2
