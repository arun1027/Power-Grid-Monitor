web: cd $(dirname $(find /var/app/current -maxdepth 2 -name "application.py" | head -n 1)) && gunicorn --bind 0.0.0.0:8000 application:application
