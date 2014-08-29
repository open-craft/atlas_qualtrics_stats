
# Database

The app relies on a SQL database to store statistics specifications and results.

## Backend DB

Both SQLite and MySQL are supported. See the config to choose between the two.

IMPORTANT: the MySQL DB needs to be utf8.

## Schema

### API_KEYS

This table holds the valid `API_key` values.

Columns:

* STRING `key` PRIMARY_KEY

### JOBS

This table holds both statistics specifications and results.

Columns:

* STRING `id` PRIMARY_KEY: the API `<stat-id>`
* STRING `API_key` PRIMARY_KEY FOREIGN_KEY: the owner API_KEYS.`key`
* TEXT `xml_spec`: the uploaded XML job specification
* TEXT `value`: the JSON statistics result
* DATETIME `created`
* DATETIME `last_run`
