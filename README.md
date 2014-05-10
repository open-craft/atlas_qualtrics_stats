
# Qualtrics statistics generator

## Installation

Will run on Python 3.3 or 3.4.

`pip install -r requirements.txt`

## Usage

```
Generate and serve statistics for a Qualtrics survey.

Usage:
  qualtrics_stats generate [--override=<file>] <survey_xml_spec>
  qualtrics_stats cron [--override=<file>] [--db=<conn-string>]
  qualtrics_stats serve [--override=<file>] [--db=<conn-string>] [--listen=<addr>]
  qualtrics_stats gen_API_key [--db=<conn-string>]
  qualtrics_stats (-h | --help)
  qualtrics_stats --version

generate will run a job one-off;
cron is meant to be run by a cronjob, generates all statistics in the db;
serve will run a web server exposing the REST API;
gen_API_key adds to the db and prints a new random API_key.

Generation options:
  --override=FILE  Read the csv from a file instad of from the API
                   PLEASE NOTE THAT THIS IS INTENDED FOR DEVELOPMENT ONLY

Server options:
  --listen=ADDR    Specify the address to listen on [default: 0.0.0.0:8080]

Database options:
  --db=CONN_STR    A SQLAlchemy connection string [default: sqlite:///qualtrics_stats.db]

General options:
  -h --help        Show this screen.
  --version        Show version.
```

## XML survey specification

A XML specification of a Qualtrics statistics is at the top a `qualtrics` tag with two attributes, `user` and `password`, the login details for the Qualtrics account, and inside that a `survey` tag with the following attributes:

* `qualtrics_survey_id`: the Qualtrics ID for the survey, it comes in this format `SV_*`
* `country_column`: the 0-indexed column (of the CSV) holding the Country answer

```xml
<qualtrics user="xx@filippo.io" password="XXXXXXXXXXXX">
	<survey qualtrics_survey_id="SV_0pQ0bjc02t8PNDT" country_column="11">
		...
	</survey>
</qualtrics>
```

Inside the survey tag go one or more of the following question tags. 

All the question tags have a `title` attribute, that is the display name for that question.

All the column numbers are 0-indexed.

### MRQ

```xml
<mrq title="MRQ" columns="18-21" />
```

The `columns` attribute is in the format `START-END` and specifies the columns holding all the possible answers (*"None of these"* excluded), `START` and `END` included. (In the example above the MRQ has 4 possible answers, 18, 19, 20, 21)

The average number of selected answers will be shown.

### Slider

```xml
<slider title="Slider" column="15" max="100" min="0" />
```

The average value of the slider will be shown.

To scale the gradient color it is recommended that max and min values are specified, otherwise they will be the highest and lowest answer given overall.

### Rank order

```xml
<rank title="Rank order">
    <option title="A" column="12" />
    <option title="B" column="13" />
    <option title="C" column="14" />
</rank>
```

Each option has its own display title, that will be shown for the most selected one (i.e. "Rank order - Brazil: B").

## API and database

See [`API.md`](API.md) for the exposed REST API docs, and [`DATABASE.md`](DATABASE.md) for the SQLite database schema.

## Testing

```
pip install -r requirements_test.txt
nosetests --rednose --verbose
```

Coverage:

```
nosetests --with-coverage --cover-package=qualtrics_stats
```

See also the following files for example input/output:

* [`exampleSurvey.xml`](qualtrics_stats/exampleSurvey.xml): `<survey_xml_spec>`
* [`edX_test.csv`](qualtrics_stats/tests/edX_test.csv): API CSV input
* [`edX_test.json`](qualtrics_stats/tests/edX_test.json): JSON output

## Sample run

```
(atlas-stats)www-data@harvard-atlas:~/atlas_qualtrics_stats$ python3 -m qualtrics_stats generate --override=qualtrics_stats/tests/edX_test.csv qualtrics_stats/exampleSurvey.xml
2014-04-23 01:24:13,404 [INFO] Loaded survey SV_0pQ0bjc02t8PNDT with 3 questions
2014-04-23 01:24:13,405 [INFO] Making Qualtrics API call...
2014-04-23 01:24:13,453 [INFO] Starting new HTTPS connection (1): new.qualtrics.com
2014-04-23 01:24:14,284 [INFO] Overriding csv source.
2014-04-23 01:24:14,287 [INFO] Starting to fetch and parse data...
2014-04-23 01:24:14,288 [INFO] Dumping results to JSON...
```
