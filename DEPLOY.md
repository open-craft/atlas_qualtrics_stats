# nginx and uwsgi deploy

In order to deploy with nginx and uwsgi:

* create a virtualenv in the repositoy root, name it `ENV` and install the requirements
* start uwsgi with the provided `uwsgi.ini` file
* configure nginx as follows

```
location / { try_files $uri @atlas; }
location @atlas {
        include uwsgi_params;
        uwsgi_pass unix:/tmp/uwsgi.sock;
}
```

# MySQL

To deploy on MySQL, do the following:

* create a `qualtrics_stats` database

```
mysql> CREATE DATABASE qualtrics_stats;
```

* set the `DB_CONN_STRING` in `config.py` to the MySQL one
