"""Generate and serve statistics for a Qualtrics survey.

Usage:
  qualtrics_stats generate [--override=<file>] <survey_xml_spec>
  qualtrics_stats cron
  qualtrics_stats serve
  qualtrics_stats (-h | --help)
  qualtrics_stats --version

Generate options:
  --override=FILE  Read the csv from a file instad of from the API

General options:
  -h --help        Show this screen.
  --version        Show version.

"""

import logging
from docopt import docopt
# from lockfile import FileLock

from .generate import QualtricsStats

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')


arguments = docopt(__doc__, version='Qualtrics Stats 0.2')

if arguments['generate']:
    csv = open(arguments['--override']) if arguments['--override'] else None
    QS = QualtricsStats(arguments['<survey_xml_spec>'], csv)
    print(QS.run())

# lock = FileLock("/tmp/qualtrics_stats.lock")
# if lock.is_locked():
#     logging.error('Lockfile locked, exiting.')
#     sys.exit(1)
# with lock:
#     main()
