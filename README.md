[![Build Status](https://travis-ci.org/cmu-db/dbdb.io.svg?branch=master)](https://travis-ci.org/cmu-db/dbdb.io)

# Database of Databases

## Installation
Assumes installation within a virtual directory

1. `pip install -U -r requirements.txt`
2. `pip install -U pip setuptools`
3. `./bin/install_xapian.sh 1.4.14`

## Deployment
Run `deploy/update_dbdb_app.sh` on the production machine to fetch new changes, run migrations, and restart the wsgi server
