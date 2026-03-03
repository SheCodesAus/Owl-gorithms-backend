release: python main/manage.py migrate
web: gunicorn --pythonpath main main.wsgi --log-file