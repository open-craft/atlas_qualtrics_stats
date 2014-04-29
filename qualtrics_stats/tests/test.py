import unittest
import random
import pep8
import json
import time
import os
import glob
import datetime

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

        super(CSVOverrideTestMixin, self).setUp()


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
        from ..db import init_db
        init_db('sqlite:///.qualtrics_stats_tests.db')

        super(DBTestMixin, self).setUp()

    def tearDown(self):
        os.remove('.qualtrics_stats_tests.db')

        super(DBTestMixin, self).setUp()


class TestGenAPIKey(DBTestMixin, unittest.TestCase):
    def test_new_API_key(self):
        from ..db import Session, API_key, gen_API_key
        session = Session()

        new_API_key = gen_API_key()

        self.assertEqual(session.query(API_key).filter(API_key.key == new_API_key).count(), 1)


class TestCron(CSVOverrideTestMixin, DBTestMixin, unittest.TestCase):
    def test_cron_execution(self):
        from ..db import Session, Job
        session = Session()

        with open(os.path.join(TEST_DIR, '../exampleSurvey.xml'), mode='rb') as f:
            xml_spec = f.read()

        job = Job(id="test", API_key="test",
                  created=datetime.datetime.utcnow(),
                  xml_spec=xml_spec)
        session.add(job)
        session.commit()

        from ..cron import cron
        cron()

        job = session.query(Job).filter(Job.id == "test").one()
        with open(os.path.join(TEST_DIR, 'edX_test.json')) as f:
            self.assertEqual(json.loads(job.value), json.load(f))
