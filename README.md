
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

See the following files for example input/output:

* [`exampleSurvey.xml`](exampleSurvey.xml): `<survey_xml_spec>` (XML specification of the statistics to generate)
* [`edX_test.csv`](edX_test.csv): API CSV input
* [`edX_test.json`](edX_test.json): JSON output

## Testing

```
pip install -r requirements_test.txt
nosetests --rednose --verbose
```