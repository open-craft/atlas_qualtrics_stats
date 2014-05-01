
# API

A REST API is exposed to retrieve statistics and schedule new ones.

The API is designed to run over HTTPS.

## Authentication

A `API_key` GET parameter must be included in all calls. There is no way to remotely generate keys, they must be created locally with the `gen_API_key` command.

Each `API_key` owns the statistics jobs it created and can retrieve results only for them.

All methods will return **403** on a not existing `API_key`.

## XML spec errors

If the XML specification of a job is malformed, a GET request for that job will return a JSON object with only one key, `error`, containing the error message.

## Methods

### GET `/stat/<stat-id>`

Retrieve the JSON result of the statistics job `<stat-id>`.

**200** on success, **404** if the job does not exist, **202** if it exists but it is not ready yet.

### PUT `/stat/<stat-id>`

*Body*: the XML specification of the statistics job. See [`exampleSurvey.xml`](qualtrics_stats/exampleSurvey.xml) for format.

Create, launch one-off and schedule a statistics job. It will overwrite a existing job with the same ID.

This should usually happen in reaction to a 404 GET `/stat/<stat-id>`.
