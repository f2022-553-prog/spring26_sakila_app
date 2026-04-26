# Author: Abtaha
# Date: 2026-04-26
# Purpose: Database configuration for Sakila Flask Application
# Team Member: Abtaha
# Health check configuration merged from feature/add-healthcheck

import os

MYSQL_HOST = os.environ.get('MYSQL_HOST', 'sakila-db-server')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DB = os.environ.get('MYSQL_DB', 'sakila')
CONNECTION_TIMEOUT = int(os.environ.get('CONNECTION_TIMEOUT', '30'))
HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', '10'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')