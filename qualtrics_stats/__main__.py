"""Generate and serve statistics for a Qualtrics survey.

Usage:
  qualtrics_stats generate [--override=<file>] <survey_xml_spec>
  qualtrics_stats cron [--override=<file>]
  qualtrics_stats serve [--listen=<addr>]
  qualtrics_stats gen_API_key
  qualtrics_stats (-h | --help)
  qualtrics_stats --version

generate will run a job one-off;
cron is meant to be run by a cronjob, generates all statistics in the db;
serve will run a web server exposing the REST API;
gen_API_key adds to the db and prints a new random API_key.

Generate and cron options:
  --override=FILE  Read the csv from a file instad of from the API

Serve options:
  --listen=ADDR    Specify the address to listen on [default: 0.0.0.0:8080]

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


arguments = docopt(__doc__, version='Qualtrics Stats 0.3.2')

if arguments['generate']:
    from .generate import QualtricsStats
    csv_override = open(arguments['--override']) if arguments['--override'] else None
    QS = QualtricsStats(arguments['<survey_xml_spec>'], csv_override)
    print(QS.run())

if arguments['cron']:
    from .cron import cron
    csv_override = open(arguments['--override']) if arguments['--override'] else None
    lock = FileLock("/tmp/qualtrics_stats.lock")
    if lock.is_locked():
        logging.error('Lockfile locked, exiting.')
        sys.exit(1)
    with lock:
        cron(csv_override)

if arguments['gen_API_key']:
    from .db import gen_API_key
    print(gen_API_key())
