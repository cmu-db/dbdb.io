Carnegie Mellon Encyclopedia of Database Systems
============

## Requirements

### Ubuntu Packages

```
python-pip
libmysqlclient-dev
```
### Python Packages

Execute this command:
```
pip install -r requirements.txt
```

## Installation Instructions

1. Clone repository
```bash
git clone https://github.com/cmu-db/dbdb.io.git
```

2. Create a symlink for the static admin files
```bash
ln -s /usr0/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin website/static/admin
```

3. Configure the mysql service (as root user) to use Barracuda for InnoDB, so `ROW_FORMAT=DYNAMIC` can be used. You only have to do this once per installation and it is not necesary on newer versions of MySQL.
```bash
sudo su
printf '\n[mysqld]\ninnodb_file_format=Barracuda\n' >> /etc/mysql/my.cnf
service mysql restart
```

4. To start from scratch, drop the database and recreate it:
```bash
mysqladmin drop -u <user> -p dbdb_io
mysqladmin create -u <user> -p dbdb_io
```

5.  To avoid issues with migrations if you already have migrations for this app. you should first delete all files from `systems/migrations` EXCEPT for the `__init__.py` and `__init__.pyc` files

  * Apply migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

  * To be able to fit the large rows in SystemVersion, apply this fix in MySQL on the database:
```sql
ALTER TABLE systems_systemversion ROW_FORMAT=DYNAMIC
```

6. Load in the initial data from the `current_data` directory:
```bash
cd current_data
python ./parse_system_data.py
```

   Load all fixtures - including new ones added by the `parse_system_data` script. There will be some output saying which fields don't match if they aren't formatted or written correctly.  
```bash
python manage.py loaddata systems/fixtures/*
```

7. Create the super user
```
python ./manage.py createsuperuser
```