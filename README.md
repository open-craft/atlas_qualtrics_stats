
# Qualtrics statistics generator

## Installation

Will run on Python 3.3 or 3.4.

`pip install -r requirements.txt`

## Usage

```
Generate and serve statistics for a Qualtrics survey.

Usage:
  qualtrics_stats generate [--override=<file>] <survey_xml_spec>
  qualtrics_stats cron [--override=<file>]
  qualtrics_stats serve [--override=<file>]
  qualtrics_stats gen_API_key
  qualtrics_stats (-h | --help)
  qualtrics_stats --version

generate will run a job one-off;
cron is meant to be run by a cronjob, generates all statistics in the db and
  saves them in CRON_RESULTS_PATH;
serve will run a web server exposing the REST API;
gen_API_key adds to the db and prints a new random API_key.

Generation options:
  --override=FILE  Read the csv from a file instad of from the API
                   PLEASE NOTE THAT THIS IS INTENDED FOR DEVELOPMENT ONLY

General options:
  -h --help        Show this screen.
  --version        Show version.
```

A `config.py` file inside the package holds the following options:

```
# A SQLAlchemy connection string
DB_CONN_STRING = 'sqlite:///qualtrics_stats.db'
# DB_CONN_STRING = 'mysql+oursql://root:password@localhost/qualtrics_stats'

# Address and port to listen on on `serve`
SERVER_LISTEN_ADDR = '0.0.0.0:8080'

# Where cron creates the json results
# {} -> job.id
CRON_RESULTS_PATH = "./json/{}.json"
```

## XML survey specification

A XML specification of a Qualtrics statistic is at the top a `qualtrics` tag with two attributes:

* `user`: the internal username for access to the API
* `password`: the API Token as generated from Account Settings

And inside that a `survey` tag with the following attributes:

* `qualtrics_survey_id`: the Qualtrics ID for the survey, it comes in this format `SV_*`
* `country_column`: the 0-indexed column (of the CSV) holding the Country answer

```xml
<qualtrics user="XXXXXXXXXXXX#xxxxxx" password="XXXXXXXXXXXX">
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
<mrq title="MRQ" columns="18-21" ignore_column="23" />
```

The `columns` attribute is in the format `START-END` and specifies the columns holding all the possible answers, `START` and `END` included. (In the example above the MRQ has 4 possible answers, 18, 19, 20, 21)

If you have, as recommended, a *"None of these"* option, do not include it in `columns`.

If you have a *"I'm not sure"* option, set it in `ignore_column`, so that the answer is not counted as a 0 (it will not be counted at all).

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

### Custom countries HTML

The `<qualtrics>` tag can also (optionally) contain a `country_messages` tag, to show a custom message on countries summary pages.

For each country, add a `<country>` tag to the `country_messages` tag, with a `name` attribute spelled like in the [`countries.txt`](countries.txt) list, and inside that put arbitrary HTML.

```xml
<country_messages>
  <country name="Côte d'Ivoire">
    Some arbitrary text ✓
  </country>
  <country name="Italy">
    or <code>HTML</code>
  </country>
</country_messages>
```

## API and database

See [`API.md`](API.md) for the exposed REST API docs, and [`DATABASE.md`](DATABASE.md) for the SQLite database schema.

## Notes on questionnaires

There are a small number of requirements/suggestions for Qualtrics questionnaires editing:

* There must be one "What is your country?" MRQ with the options listed in [`countries.txt`](countries.txt)
* MRQ answers should be required and "None of these" + "I'm not sure" options should be offered
* Slider and rank answers should be requested (so that the user will have to confirm to leave them blank)
* Short titles will fit best
* There must not be answers with text "0" or "99999"

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

* [`exampleSurvey.xml`](qualtrics_stats/exampleSurvey.xml): XML survey specification
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
