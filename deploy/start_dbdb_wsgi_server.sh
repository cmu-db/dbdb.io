#!/bin/bash

LOG_DIR="/var/log/gunicorn"

# Find out the location of the script, not the working directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
cd $DIR/..

# Activate virtualenv
echo "# Activating virtualenv."
. ../env/bin/activate

# Kill previous gunicorn processes
echo "# Killing previous gunicorn processes."
if lsof -t -i:8000 > /dev/null; then
    kill $(lsof -t -i:8000)
fi

# Start Django with Gunicorn
echo "# Starting Django with Gunicorn on port 8000..."
gunicorn --bind 127.0.0.1:8000 -w 12 --access-logfile "$LOG_DIR/access-logfile" \
    --error-logfile "$LOG_DIR/error-logfile" dbdb.wsgi
# gunicorn --bind 127.0.0.1:8000 -w 12 dbdb.wsgi

echo "# Done."
