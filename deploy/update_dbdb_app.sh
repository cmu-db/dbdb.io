#!/bin/bash

set -e # Fail the script on any errors

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
cd $DIR/.. # Move to the root of the project

echo "# Checking out and pulling master branch."
git checkout master
git pull

echo "# Activating virtualenv."
set +e # The activate script might return non-zero even on success
. ../env/bin/activate
set -e

echo "# Installing pip requirements."
pip install -r requirements.txt

echo "# Collecting static files."
python manage.py collectstatic --noinput

echo "# Running database migrations."
python manage.py migrate --noinput

echo "# Restarting the backend service."
sudo systemctl restart dbdb.io-pg

echo "# Update done!"
