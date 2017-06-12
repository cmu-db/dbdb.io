#!/usr/bin/env bash

if [[ $# -ne 1 ]]; then
    printf '\nusage: restartdb.sh <user>\n'
    printf '\nuser: username for mysql\n'
    exit
fi

printf '\nDropping database..\n'
mysqladmin drop -u $1 -p dbdb_io

printf '\nCreating database..\n'
mysqladmin create -u $1 -p dbdb_io

printf '\nDeleting migrations..\n'
cd systems/migrations
printf '\nDeleting files:\n'
ls | grep -v '__init__'
ls | grep -v '__init__' | xargs rm
cd ../..

printf '\nCreating migrations..\n'
python manage.py makemigrations
python manage.py migrate

printf '\nCreating the initial data from the current_data directory...\n'
cd current_data
python ./parse_system_data.py
printf '\nFinished creating intial data! Please check current_data directory for error output. \n'
cd ..

printf '\nLoading fixtures...\n'
python manage.py loaddata systems/fixtures/*

printf '\nCreating the super user\n'
python manage.py createsuperuser
