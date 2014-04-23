
# Qualtrics statistics generator

## Installation

Will run on Python 3.3 or 3.4.

`pip install -r requirements.txt`

## Usage

```
Generate statistics for a Qualtrics survey.

Usage:
  qualtrics_stats.py [--override=<file>] <survey_xml_spec>
  qualtrics_stats.py (-h | --help)
  qualtrics_stats.py --version

Options:
  --override=FILE  Read the csv from a file instad of from the API
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
<slider title="Slider" column="15" />
```

The average value of the slider will be shown.

### Rank order

```xml
<rank title="Rank order">
    <option title="A" column="12" />
    <option title="B" column="13" />
    <option title="C" column="14" />
</rank>
```

Each option has its own display title, that will be shown for the most selected one (i.e. "Rank order - Brazil: B").

## Testing

```
pip install -r requirements_test.txt
nosetests --rednose --verbose
```

Coverage:

```
coverage run nosetests
coverage report -m
```

See also the following files for example input/output:

* [`testSurvey.xml`](testSurvey.xml): `<survey_xml_spec>`
* [`edX_test.csv`](edX_test.csv): API CSV input
* [`edX_test.json`](edX_test.json): JSON output