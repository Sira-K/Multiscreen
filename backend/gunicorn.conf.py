# backend/gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
timeout = 600
max_requests = 1000
access_logfile = "logs/access.log"
error_logfile = "logs/error.log"