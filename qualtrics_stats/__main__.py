"""Generate and serve statistics for a Qualtrics survey.

Usage:
  qualtrics_stats generate [--override=<file>] <survey_xml_spec>
  qualtrics_stats cron [--override=<file>]
  qualtrics_stats serve [--override=<file>]
  qualtrics_stats gen_API_key
  qualtrics_stats (-h | --help)
  qualtrics_stats --version

generate will run a job one-off;
cron is meant to be run by a cronjob, generates all statistics in the db and
  saves them in "./json/<job_id>.json";
serve will run a web server exposing the REST API;
gen_API_key adds to the db and prints a new random API_key.

Generation options:
  --override=FILE  Read the csv from a file instad of from the API
                   PLEASE NOTE THAT THIS IS INTENDED FOR DEVELOPMENT ONLY

General options:
  -h --help        Show this screen.
  --version        Show version.

"""

import logging
import sys
from docopt import docopt
from lockfile import FileLock

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')


arguments = docopt(__doc__, version='Qualtrics Stats 0.4.0')

if arguments['cron'] or arguments['serve'] or arguments['gen_API_key']:
    from .db import init_db
    from .config import DB_CONN_STRING
    init_db(DB_CONN_STRING)

if arguments['generate'] or arguments['cron'] or arguments['serve']:
    from . import generate
    generate.csv_override = open(arguments['--override']) if arguments['--override'] else None


if arguments['generate']:
    from .generate import QualtricsStats
    QS = QualtricsStats(arguments['<survey_xml_spec>'])
    print(QS.run())

if arguments['cron']:
    from .cron import cron
    lock = FileLock("/tmp/qualtrics_stats.lock")
    if lock.is_locked():
        logging.error('Lockfile locked, exiting.')
        sys.exit(1)
    with lock:
        cron()

if arguments['serve']:
    from .server import serve
    from .config import SERVER_LISTEN_ADDR
    serve(SERVER_LISTEN_ADDR)

if arguments['gen_API_key']:
    from .db import gen_API_key
    print(gen_API_key())
