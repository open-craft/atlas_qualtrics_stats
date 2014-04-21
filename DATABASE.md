
# Database

The app relies on a SQLite database to store statistics specifications and results.

## Schema

### API_KEYS

This table holds the valid `API_key` values.

Columns:

* TEXT `key`

### JOBS

This table holds both statistics specifications and results.

Columns:

* TEXT `id`: the API `<stat-id>`
* TEXT `API_key`: the owner API_KEYS.`key`
* TEXT `xml_spec`: the uploaded XML job specification
* TEXT `value`: the JSON statistics result
* DATETIME `created`
* DATETIME `last_run`