#!/bin/bash

sudo apt update
sudo apt install pkg-config libmysqlclient-dev build-essential -y

# shellcheck disable=SC2164
cd "$(pwd)/zascapay"
python manage.py makemigrations
python manage.py migrate
python runserver.py