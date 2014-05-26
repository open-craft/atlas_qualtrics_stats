import logging
import datetime
import os.path
import os
from io import StringIO

from .db import Session, Job
from .generate import QualtricsStats


def cron():
    session = Session()

    if not os.path.exists(os.path.join('.', 'json')):
        os.makedirs(os.path.join('.', 'json'))

    for job in session.query(Job):
        logging.info('Running job {}...'.format(job.id))

        QS = QualtricsStats(StringIO(job.xml_spec))
        job.value = QS.run()
        job.last_run = datetime.datetime.utcnow()

        filename = os.path.join('.', 'json', job.id + '.json')
        with open(filename, 'w') as f:
            f.write(job.value)
        logging.info('Saved the result to db and {}'.format(filename))

    session.commit()
