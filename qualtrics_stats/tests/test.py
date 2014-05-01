import unittest
import random
import pep8
import json
import time
import os
import glob
import datetime
import threading

TEST_DIR = os.path.dirname(os.path.realpath(__file__))


class TestCodeFormat(unittest.TestCase):
    def test_pep8_conformance(self):
        pep8style = pep8.StyleGuide(quiet=True, config_file='setup.cfg')
        result = pep8style.check_files(
            glob.glob(os.path.join(TEST_DIR, '../*.py')) +
            glob.glob(os.path.join(TEST_DIR, '*.py')))
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")


class TestRunningAverage(unittest.TestCase):
    def test_average_result(self):
        from ..running_average import RunningAverage

        random.seed('running_average_test')  # to make the test deterministic
        values = [random.randint(0, 10) for _ in range(1000000)]

        true_avg = float(sum(values))/len(values)

        A = RunningAverage()
        for v in values:
            A.add(v)

        self.assertAlmostEqual(A.average, true_avg)


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


class DBTestMixin():
    def setUp(self):
        if os.path.isfile('.qualtrics_stats_tests.db'):
            os.remove('.qualtrics_stats_tests.db')

        from ..db import init_db
        init_db('sqlite:///.qualtrics_stats_tests.db')

        super(DBTestMixin, self).setUp()

    def tearDown(self):
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

    def get_tst_job(self, id="test", API_key="test"):
        from ..db import Session, Job
        session = Session()

        job = session.query(Job).filter(Job.API_key == API_key,
                                        Job.id == "test").one()

        return job


class TestGenAPIKey(DBTestMixin, unittest.TestCase):
    def test_new_API_key(self):
        from ..db import Session, API_key, gen_API_key
        session = Session()

        new_API_key = gen_API_key()

        self.assertEqual(session.query(API_key).filter(API_key.key == new_API_key).count(), 1)


class TestCron(CSVOverrideTestMixin, DBTestMixin, unittest.TestCase):
    def test_cron_execution(self):
        self.new_tst_job()

        from ..cron import cron
        cron()

        job = self.get_tst_job()
        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            self.assertEqual(json.loads(job.value), json.load(f))


class TestServer(CSVOverrideTestMixin, DBTestMixin, unittest.TestCase):
    def setUp(self):
        super(TestServer, self).setUp()

        from ..server import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_bad_API_key(self):
        rv = self.app.get('/stat/foo?API_key=not_existing')
        self.assertEqual(rv.status_code, 403)
        self.assertIn(b'API_key not valid', rv.get_data())

        rv = self.app.put('/stat/foo?API_key=not_existing')
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

        self.new_tst_job(id="test", API_key="test")

        rv = self.app.get('/stat/test?API_key=' + API_key)
        self.assertEqual(rv.status_code, 404)
        self.assertIn(b'No job with that stat-id found', rv.get_data())

    def test_GET_202(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job(id="test", API_key=API_key)

        rv = self.app.get('/stat/test?API_key=' + API_key)
        self.assertEqual(rv.status_code, 202)
        self.assertIn(b'Value is still not ready, try again later', rv.get_data())

    def test_GET_200(self):
        from ..db import gen_API_key
        API_key = gen_API_key()

        self.new_tst_job(id="test", API_key=API_key)

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
