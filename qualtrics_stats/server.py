import datetime
import logging
import functools
import binascii
import scrypt
import uuid
import flask
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from flask import Flask, Response
from flask import request
from flask import render_template, redirect, abort, url_for
from flask_sslify import SSLify
from threading import Thread
from io import StringIO

from .generate import QualtricsStats
from .db import Session, Job, API_key
from .config import ADMIN_USER, ADMIN_PASS


### Globals

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
# sslify = SSLify(app)


### Helpers

def get_API_key(check_key=True):
    """
    Get and optionally verify the API_key from the GET string
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            key = request.args.get('API_key')
            if not key:
                return 'API_key not valid', 403
            session = Session()
            if check_key and not session.query(API_key).filter(API_key.key == key).count():
                return 'API_key not valid', 403

            return f(*args, key=key, **kwargs)
        return decorated
    return decorator


def run_job(stat_id, API_key):
    """
    Run a statistic job
    """
    logging.info('Running job {}...'.format(stat_id))

    session = Session()
    job = session.query(Job).filter(Job.API_key == API_key,
                                    Job.id == stat_id).one()

    QS = QualtricsStats(StringIO(job.xml_spec))
    job.value = QS.run()
    job.last_run = datetime.datetime.utcnow()

    session.commit()


def requires_auth(f):
    """
    Check HTTP Basic Auth
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return Response('Please login.', 401,
                            {'WWW-Authenticate': 'Basic realm="Atlas Admin Panel"'})

        hashed_password = binascii.hexlify(scrypt.hash(
            auth.password, '6cFp3RgPkd8ABVZugrbu', N=1 << 16)).decode()
        if auth.username != ADMIN_USER or hashed_password != ADMIN_PASS:
            return Response('Wrong login.', 401,
                            {'WWW-Authenticate': 'Basic realm="Atlas Admin Panel"'})

        # A API_key is generated for the user by hashing the password
        flask.g.user_API_key = binascii.hexlify(scrypt.hash(
            auth.password, 'fCo9cB4fQ7bnxGAoZcVo', N=1 << 16)).decode()[:16]

        return f(*args, **kwargs)
    return decorated


@app.before_request
def csrf_protect():
    """
    Check CSRF tokens on POST requests
    """
    if request.method == "POST":
        token = flask.session.get('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)


def generate_csrf_token():
    """
    Generate and store the CSRF token (to be used in templates)
    """
    flask.session['_csrf_token'] = str(uuid.uuid4())
    return flask.session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


### API views

@app.route("/stat/<stat_id>", methods=['GET'])
@get_API_key(check_key=False)
def get_stat(stat_id, key):
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
@get_API_key()
def put_stat(stat_id, key):
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
    job.xml_spec = request.data.decode('utf-8')
    job.last_run = job.value = None

    session.commit()

    Thread(target=run_job, args=(stat_id, key)).start()

    if overwritten:
        return 'Job successfully overwritten and scheduled'
    else:
        return 'Job successfully created and scheduled'


### Admin views

@app.route("/admin/", methods=['GET'])
@requires_auth
def admin_index():
    session = Session()
    jobs = session.query(Job).filter(Job.API_key == flask.g.user_API_key)
    return render_template('admin.html', jobs=jobs)


@app.route("/admin/new", methods=['GET'])
@requires_auth
def admin_new():
    return render_template('new.html')


@app.route("/admin/new", methods=['POST'])
@requires_auth
def admin_new_submit():
    stat_id = request.form["name"]
    if '/' in stat_id or '?' in stat_id or not stat_id:
        return 'Invalid name', 400

    session = Session()
    if session.query(Job).filter(Job.API_key == flask.g.user_API_key,
                                 Job.id == stat_id).count():
        return 'Sorry, that job already exists', 400

    job = Job(API_key=flask.g.user_API_key, id=stat_id)
    session.add(job)
    logging.info("created new job {}".format(stat_id))

    job.created = datetime.datetime.utcnow()
    job.xml_spec = request.form["xml"]
    job.last_run = job.value = None

    session.commit()

    return redirect(url_for(".admin_index"), 303)


@app.route("/admin/edit/<stat_id>", methods=['GET'])
@requires_auth
def admin_edit(stat_id):
    session = Session()
    try:
        job = session.query(Job).filter(Job.API_key == flask.g.user_API_key,
                                        Job.id == stat_id).one()
    except NoResultFound:
        return 'Sorry, this job has not been found', 404
    return render_template('edit.html', stat_id=job.id, xml=job.xml_spec)


@app.route("/admin/edit/<stat_id>", methods=['POST'])
@requires_auth
def admin_edit_submit(stat_id):
    session = Session()
    try:
        job = session.query(Job).filter(Job.API_key == flask.g.user_API_key,
                                        Job.id == stat_id).one()
    except NoResultFound:
        return 'Sorry, this job has not been found', 404

    job.xml_spec = request.form["xml"]
    job.last_run = job.value = None

    session.commit()

    return redirect(url_for(".admin_edit", stat_id=stat_id, saved=1), 303)


@app.route("/admin/delete/<stat_id>", methods=['GET'])
@requires_auth
def admin_delete(stat_id):
    return render_template('delete.html', stat_id=stat_id)


@app.route("/admin/delete/<stat_id>", methods=['POST'])
@requires_auth
def admin_delete_submit(stat_id):
    session = Session()
    try:
        job = session.query(Job).filter(Job.API_key == flask.g.user_API_key,
                                        Job.id == stat_id).one()
    except NoResultFound:
        return 'Sorry, this job has not been found', 404

    session.delete(job)
    session.commit()

    return redirect(url_for(".admin_index"), 303)


### Main

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
