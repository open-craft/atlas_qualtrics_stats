import logging
import datetime
from io import StringIO

from .db import Session, Job
from .generate import QualtricsStats


def cron(csv_override=None):
    session = Session()

    for job in session.query(Job):
        logging.info('Running job {}...'.format(job.id))

        QS = QualtricsStats(StringIO(job.xml_spec), csv_override)
        job.value = QS.run()
        job.last_run = datetime.datetime.utcnow()

    session.commit()
