import unittest
import random
import pep8
import json
import time
import os
import glob
import datetime
import threading
import io
import re
import shutil
import base64
import binascii
import scrypt

TEST_DIR = os.path.dirname(os.path.realpath(__file__))

unittest.TestCase.maxDiff = None


class TestCodeFormat(unittest.TestCase):
    def test_pep8_conformance(self):
        pep8style = pep8.StyleGuide(quiet=True, config_file='setup.cfg')
        result = pep8style.check_files(
            glob.glob(os.path.join(TEST_DIR, '../*.py')) +
            glob.glob(os.path.join(TEST_DIR, '*.py')))
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings): {}".format(result.print_statistics()))


class TestRunningAverage(unittest.TestCase):
    def test_average_result(self):
        from ..running_average import RunningAverage

        random.seed('running_average_test')  # to make the test deterministic
        values = [random.uniform(1, 10) for _ in range(1000000)]

        true_avg = float(sum(values)) / len(values)
        true_max = max(values)
        true_min = min(values)

        A = RunningAverage()
        for v in values:
            A.add(v)

        self.assertAlmostEqual(A.average, true_avg)
        self.assertEqual(A.max, true_max)
        self.assertEqual(A.min, true_min)


class CSVOverrideTestMixin():
    def setUp(self):
        from .. import generate
        self._csv_file = open(os.path.join(TEST_DIR, 'edX_test.csv'))
        generate.csv_override = self._csv_file

        super(CSVOverrideTestMixin, self).setUp()

    def tearDown(self):
        from .. import generate
        generate.csv_override = None
        self._csv_file.close()

        super(CSVOverrideTestMixin, self).tearDown()


class TestGeneration(CSVOverrideTestMixin, unittest.TestCase):
    def test_stats_result(self):
        from .. import generate
        QS = generate.QualtricsStats(os.path.join(TEST_DIR, '../exampleSurvey.xml'))
        res = json.loads(QS.run())

        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            self.assertEqual(res, json.load(f))

    def test_no_mrq_ignore(self):
        from .. import generate
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            xml = f.read()
        if 'ignore_column="23"' not in xml:
            self.fail('exampleSurvey.xml changed, test does not apply anymore')
        xml = xml.replace('ignore_column="23"', '')
        QS = generate.QualtricsStats(io.StringIO(xml))
        res = json.loads(QS.run())

        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            js_test = json.load(f)
            js_test["statistics"][0] = {
                "countries": {
                    "Tuvalu": 1.5,
                    "Brazil": 2.0
                },
                "title": "MRQ",
                "type": "mrq",
                "average": 1.25,
                "max": 4,
                "min": 0
            }
            self.assertEqual(res, js_test)

    def test_slider_auto_min_max_result(self):
        from .. import generate
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            xml = f.read()
        if 'max="100.0" min="0"' not in xml:
            self.fail('exampleSurvey.xml changed, test does not apply anymore')
        xml = xml.replace('max="100.0" min="0"', '')
        QS = generate.QualtricsStats(io.StringIO(xml))
        res = json.loads(QS.run())

        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            js_test = json.load(f)
            js_test["statistics"][1]["max"] = 30
            js_test["statistics"][1]["min"] = 6
            self.assertEqual(res, js_test)

    def test_title_html_unescape(self):
        from .. import generate
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            xml = f.read()
        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            js_test = json.load(f)
            for i, t in enumerate(('MRQ', 'Slider', 'Rank order')):
                xml = xml.replace('title="{}'.format(t), 'title="&lt;br /&gt;{}'.format(t))
                js_test["statistics"][i]["title"] = '<br />{}'.format(t)

        QS = generate.QualtricsStats(io.StringIO(xml))
        res = json.loads(QS.run())
        self.assertEqual(res, js_test)

    def test_100K_lines_performance(self):
        def csv_lines_repetitor():
            f = open(os.path.join(TEST_DIR, 'edX_test.csv'))
            for i in range(2):
                yield next(f)
            file_lines = f.readlines()
            line_count = 0
            while line_count < 100000:
                for line in file_lines:
                    line_count += 1
                    yield line

        from .. import generate
        generate.csv_override = csv_lines_repetitor()

        QS = generate.QualtricsStats(os.path.join(TEST_DIR, '../exampleSurvey.xml'))

        start = time.time()
        json_output = QS.run()
        self.assertLess(time.time() - start, 20)

        res = json.loads(json_output)

        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            ref = json.load(f)

        for n, stat in enumerate(res['statistics']):
            if 'average' in stat:
                self.assertAlmostEqual(stat['average'],
                                       ref['statistics'][n]['average'])
                stat['average'] = ref['statistics'][n]['average'] = 1

        self.assertEqual(res, ref)

    def test_malformed_xmls(self):
        pairs = (
            ('malformed.1.xml', 'XML parsing error: junk after document element: line 3, column 0'),
            ('malformed.2.xml', 'survey tag missing'),
            ('malformed.3.xml', 'qualtrics tag attribute "user" missing'),
            ('malformed.4.xml', 'survey tag attribute "country_column" missing'),
            ('malformed.5.xml', 'mrq tag attribute "title" missing'),
            ('malformed.6.xml', 'mrq tag attribute "columns" format should be NN-NN'),
            ('malformed.7.xml', 'slider tag attribute "title" missing'),
            ('malformed.8.xml', 'rank tag should have at least two option children'),
            ('malformed.9.xml', 'option tag attribute "column" missing'),
            ('malformed.a.xml', 'slider tag attribute "column" should be a number'),
            ('malformed.b.xml', 'option tag attribute "column" should be a number'),
            ('malformed.c.xml', 'slider tag attribute "max" should be a number'),
            ('malformed.d.xml', 'mrq tag attribute "ignore_column" should be a number'),
            ('malformed.e.xml', 'country tag missing the "name" attribute'),
            ('malformed.f.xml', 'unknown tag inside the "country_messages" tag'),
        )

        for filename, error in pairs:
            from .. import generate
            with self.assertLogs(level='ERROR') as cm:
                QS = generate.QualtricsStats(os.path.join(TEST_DIR, filename))
            self.assertEqual(cm.output, ['ERROR:root:' + error])
            res = json.loads(QS.run())
            self.assertEqual(res['error'], error)

    def test_no_country_messages(self):
        from .. import generate
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            xml = f.read()
        xml = re.sub('(?s)<country_messages>.*</country_messages>', '', xml)
        QS = generate.QualtricsStats(io.StringIO(xml))
        res = json.loads(QS.run())

        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            js_test = json.load(f)
            js_test["country_messages"] = {}
            self.assertEqual(res, js_test)


class DBTestMixin():
    def setUp(self):
        if os.path.isfile('.qualtrics_stats_tests.db'):
            os.remove('.qualtrics_stats_tests.db')

        from ..db import init_db
        init_db('sqlite:///.qualtrics_stats_tests.db')
        # init_db('mysql+oursql://root:password@localhost/qualtrics_stats_test', drop_all=True)

        from ..db import Session, API_key
        session = Session()
        api_key = API_key(key="test")
        session.add(api_key)
        session.commit()

        super(DBTestMixin, self).setUp()

    def tearDown(self):
        from ..db import Session
        Session.remove()
        os.remove('.qualtrics_stats_tests.db')

        super(DBTestMixin, self).tearDown()

    def new_tst_job(self, id="test", API_key="test", xml_spec=None):
        from ..db import Session, Job
        session = Session()

        if xml_spec is None:
            with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
                xml_spec = f.read()

        job = Job(id=id, API_key=API_key,
                  created=datetime.datetime.utcnow(),
                  xml_spec=xml_spec)
        session.add(job)
        session.commit()

    def get_tst_job(self, job_id="test", API_key="test"):
        from ..db import Session, Job
        session = Session()

        job = session.query(Job).filter(Job.API_key == API_key,
                                        Job.id == job_id).one()

        session.close()
        return job


class TestGenAPIKey(DBTestMixin, unittest.TestCase):
    def test_new_API_key(self):
        from ..db import Session, API_key, gen_API_key
        session = Session()

        new_API_key = gen_API_key()

        self.assertEqual(session.query(API_key).filter(API_key.key == new_API_key).count(), 1)

        session.close()


class CronTestMixin():
    def setUp(self):
        # Make sure that we don't nuke a existing json folder on tearDown
        if os.path.exists('json'):
            os.rmdir('json')

        super(CronTestMixin, self).setUp()

    def tearDown(self):
        if os.path.exists('json'):
            shutil.rmtree('json')

        super(CronTestMixin, self).tearDown()


class TestCron(CSVOverrideTestMixin, DBTestMixin, CronTestMixin, unittest.TestCase):
    def test_cron_execution(self):
        self.new_tst_job()

        from ..cron import cron
        cron()

        job = self.get_tst_job()
        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            self.assertEqual(json.loads(job.value), json.load(f))

        with open(os.path.join('json', job.id + '.json')) as f:
            self.assertEqual(json.loads(job.value), json.load(f))


class TestServer(CSVOverrideTestMixin, DBTestMixin, CronTestMixin, unittest.TestCase):
    def setUp(self):
        super(TestServer, self).setUp()

        from ..server import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_bad_API_key(self):
        rv = self.app.put('/stat/foo?API_key=not_existing')
        self.assertEqual(rv.status_code, 403)
        self.assertIn(b'API_key not valid', rv.get_data())

    def test_no_API_key(self):
        rv = self.app.put('/stat/foo')
        self.assertEqual(rv.status_code, 403)
        self.assertIn(b'API_key not valid', rv.get_data())

    def test_GET_404(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        rv = self.app.get('/stat/foo?API_key=' + API_key)
        self.assertEqual(rv.status_code, 404)
        self.assertIn(b'No job with that stat-id found', rv.get_data())

    def test_GET_404_wrong_API_key(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job()

        rv = self.app.get('/stat/test?API_key=' + API_key)
        self.assertEqual(rv.status_code, 404)
        self.assertIn(b'No job with that stat-id found', rv.get_data())

    def test_GET_202(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job(API_key=API_key)

        rv = self.app.get('/stat/test?API_key=' + API_key)
        self.assertEqual(rv.status_code, 202)
        self.assertIn(b'Value is still not ready, try again later', rv.get_data())

    def test_GET_200(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job(API_key=API_key)

        from ..cron import cron
        cron()

        rv = self.app.get('/stat/test?API_key=' + API_key)
        self.assertEqual(rv.status_code, 200)
        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            self.assertEqual(json.loads(rv.get_data().decode()), json.load(f))

    def test_PUT_new(self):
        threading.enumerate()[0]

        from ..db import gen_API_key
        API_key = gen_API_key()

        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml'), mode='rb') as f:
            rv = self.app.put('/stat/test?API_key=' + API_key, input_stream=f)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Job successfully created and scheduled', rv.get_data())

        job = self.get_tst_job(API_key=API_key)
        self.assertEqual(job.id, "test")
        self.assertEqual(job.API_key, API_key)
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            self.assertEqual(job.xml_spec, f.read())
        self.assertIsNone(job.value)
        self.assertIsNone(job.last_run)
        self.assertLess(datetime.datetime.utcnow() - job.created,
                        datetime.timedelta(seconds=1))

        start = time.time()
        while time.time() - start < 60:
            job = self.get_tst_job(API_key=API_key)
            if job.value:
                with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
                    self.assertEqual(json.loads(job.value), json.load(f))
                self.assertLess(datetime.datetime.utcnow() - job.last_run,
                                datetime.timedelta(seconds=2))
                break
            time.sleep(1)
        else:
            self.fail('The job did not get executed in 60s')

    def test_PUT_existing(self):
        threading.enumerate()[0]

        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job(API_key=API_key, xml_spec='')
        time.sleep(1)

        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml'), mode='rb') as f:
            rv = self.app.put('/stat/test?API_key=' + API_key, input_stream=f)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Job successfully overwritten and scheduled', rv.get_data())

        job = self.get_tst_job(API_key=API_key)
        self.assertEqual(job.id, "test")
        self.assertEqual(job.API_key, API_key)
        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml')) as f:
            self.assertEqual(job.xml_spec, f.read())
        self.assertIsNone(job.value)
        self.assertIsNone(job.last_run)
        self.assertLess(datetime.datetime.utcnow() - job.created,
                        datetime.timedelta(seconds=1))

        start = time.time()
        while time.time() - start < 60:
            job = self.get_tst_job(API_key=API_key)
            if job.value:
                with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
                    self.assertEqual(json.loads(job.value), json.load(f))
                self.assertLess(datetime.datetime.utcnow() - job.last_run,
                                datetime.timedelta(seconds=2))
                break
            time.sleep(1)
        else:
            self.fail('The job did not get executed in 60s')


class TestAdmin(CSVOverrideTestMixin, DBTestMixin, CronTestMixin, unittest.TestCase):
    def setUp(self):
        super(TestAdmin, self).setUp()

        from .. import config
        config.ADMIN_PASS = binascii.hexlify(scrypt.hash(
            'password', '6cFp3RgPkd8ABVZugrbu', N=1 << 16)).decode()

        from ..server import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    def gen_auth(self, username='admin', password='password'):
        return {"Authorization": "Basic " + base64.b64encode(
            username.encode() + b':' + password.encode()).decode()}

    def extract_csrf_token(self, html):
        r = re.compile(r'<input name="_csrf_token" type="hidden" value="(.*?)">')
        return r.search(html).group(1)

    def test_auth(self):
        rv = self.app.get('/admin/', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)

        rv = self.app.get('/admin/')
        self.assertEqual(rv.status_code, 401)

        rv = self.app.get('/admin/', headers=self.gen_auth(password='xxx'))
        self.assertEqual(rv.status_code, 401)

    def test_csrf(self):
        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': 'xxx'})
        self.assertEqual(rv.status_code, 403)

        rv = self.app.post('/admin/new', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 403)

        self.app.get('/admin/new', headers=self.gen_auth())

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': 'xxx'})
        self.assertEqual(rv.status_code, 403)

        rv = self.app.post('/admin/new', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 403)

    def test_full_cycle(self):
        # First create a job
        rv = self.app.get('/admin/new', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        csrf_token = self.extract_csrf_token(rv.get_data().decode('utf-8'))

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'name': 'test_job',
                                 'xml': 'test body ✓'})
        self.assertEqual(rv.status_code, 303)

        # Then check that it shows up in the list
        rv = self.app.get('/admin/', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        self.assertIn('<td><code>test_job</code></td>', rv.get_data().decode('utf-8'))

        # Now edit it
        rv = self.app.get('/admin/edit/test_job', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        data = rv.get_data().decode('utf-8')
        csrf_token = self.extract_csrf_token(data)
        self.assertIn('<h3>Editing: <code>test_job</code></h3>', data)
        self.assertIn('<textarea name="xml">test body ✓</textarea>', data)

        rv = self.app.post('/admin/edit/test_job',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'xml': 'new test body ✓'})
        self.assertEqual(rv.status_code, 303)

        rv = self.app.get('/admin/edit/test_job', headers=self.gen_auth())
        data = rv.get_data().decode('utf-8')
        self.assertIn('<textarea name="xml">new test body ✓</textarea>', data)

        # Finally delete it
        rv = self.app.get('/admin/delete/test_job', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        csrf_token = self.extract_csrf_token(rv.get_data().decode('utf-8'))

        rv = self.app.post('/admin/delete/test_job',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token})
        self.assertEqual(rv.status_code, 303)

    def test_invalid_name(self):
        rv = self.app.get('/admin/new', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        csrf_token = self.extract_csrf_token(rv.get_data().decode('utf-8'))

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'name': '',
                                 'xml': 'test body ✓'})
        self.assertEqual(rv.status_code, 400)

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'name': 'test/test',
                                 'xml': 'test body ✓'})
        self.assertEqual(rv.status_code, 400)

    def test_duplicate_name(self):
        rv = self.app.get('/admin/new', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 200)
        csrf_token = self.extract_csrf_token(rv.get_data().decode('utf-8'))

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'name': 'duplicate_job',
                                 'xml': 'test body ✓'})
        self.assertEqual(rv.status_code, 303)

        rv = self.app.post('/admin/new',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'name': 'duplicate_job',
                                 'xml': 'test body ✓'})
        self.assertEqual(rv.status_code, 400)

    def test_not_existing_job(self):
        rv = self.app.get('/admin/new', headers=self.gen_auth())
        csrf_token = self.extract_csrf_token(rv.get_data().decode('utf-8'))

        rv = self.app.get('/admin/edit/not_existing_job', headers=self.gen_auth())
        self.assertEqual(rv.status_code, 404)

        rv = self.app.post('/admin/edit/not_existing_job',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token,
                                 'xml': 'new test body ✓'})
        self.assertEqual(rv.status_code, 404)

        rv = self.app.post('/admin/delete/not_existing_job',
                           headers=self.gen_auth(),
                           data={'_csrf_token': csrf_token})
        self.assertEqual(rv.status_code, 404)
