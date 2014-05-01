import datetime
import logging
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from flask import Flask, request
from threading import Thread
from io import BytesIO

from .generate import QualtricsStats
from .db import Session, Job, API_key

app = Flask(__name__)


def authenticate():
    key = request.args.get('API_key')
    session = Session()
    if not key or not session.query(API_key).filter(API_key.key == key).count():
        return False
    return key


def run_job(stat_id, API_key):
    logging.info('Running job {}...'.format(stat_id))

    session = Session()
    job = session.query(Job).filter(Job.API_key == API_key,
                                    Job.id == stat_id).one()

    QS = QualtricsStats(BytesIO(job.xml_spec))
    job.value = QS.run()
    job.last_run = datetime.datetime.utcnow()

    session.commit()


@app.route("/stat/<stat_id>", methods=['GET'])
def get_stat(stat_id):
    key = authenticate()
    if not key:
        return 'API_key not valid', 403

    session = Session()
    try:
        job = session.query(Job).filter(Job.API_key == key,
                                        Job.id == stat_id).one()
    except NoResultFound:
        return 'No job with that stat-id found', 404
    except MultipleResultsFound:
        return 'Multiple jobs with that stat-id found', 500

    if not job.value:
        return 'Value is still not ready, try again later', 202

    return job.value


@app.route("/stat/<stat_id>", methods=['PUT'])
def put_stat(stat_id):
    key = authenticate()
    if not key:
        return 'API_key not valid', 403

    overwritten = False

    session = Session()
    try:
        job = session.query(Job).filter(Job.API_key == key,
                                        Job.id == stat_id).one()
        overwritten = True
    except NoResultFound:
        job = Job(API_key=key, id=stat_id)
        session.add(job)
        logging.info("created new job {}".format(stat_id))
    except MultipleResultsFound:
        return 'Multiple jobs with that stat-id found', 500

    job.created = datetime.datetime.utcnow()
    job.xml_spec = request.data
    job.last_run = job.value = None

    session.commit()

    Thread(target=run_job, args=(stat_id, key)).start()

    if overwritten:
        return 'Job successfully overwritten and scheduled'
    else:
        return 'Job successfully created and scheduled'


def serve(addr):
    host, port = addr.split(':')
    app.run(host, int(port))


DB_SET_UP = False
def wsgi_app(*args, **kwargs):
    if not DB_SET_UP:
        from .db import init_db
        from .config import DB_CONN_STRING
        init_db(DB_CONN_STRING)
    return app(*args, **kwargs)
