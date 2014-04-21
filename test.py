import unittest
import random
import pep8
import json
import time


class TestCodeFormat(unittest.TestCase):
    def test_pep8_conformance(self):
        pep8style = pep8.StyleGuide(quiet=True, config_file='setup.cfg')
        result = pep8style.check_files([
            'running_average.py',
            'qualtrics_stats.py',
            'test.py'])
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")


class TestRunningAverage(unittest.TestCase):
    def test_average_result(self):
        from running_average import RunningAverage

        random.seed('running_average_test')  # to make the test deterministic
        values = [random.randint(0, 10) for _ in range(1000000)]

        true_avg = float(sum(values))/len(values)

        A = RunningAverage()
        for v in values:
            A.add(v)

        self.assertAlmostEqual(A.average, true_avg)


class TestQualtricsStats(unittest.TestCase):
    def test_stats_result(self):
        from qualtrics_stats import QualtricsStats

        QS = QualtricsStats('exampleSurvey.xml', open('edX_test.csv'))
        res = json.loads(QS.run())

        with open('edX_test.json') as f:
            self.assertEqual(res, json.load(f))

    def test_100K_lines_performance(self):
        def csv_lines_repetitor():
            f = open('edX_test.csv')
            for i in range(2):
                yield next(f)
            file_lines = f.readlines()
            line_count = 0
            while line_count < 100000:
                for line in file_lines:
                    line_count += 1
                    yield line

        from qualtrics_stats import QualtricsStats

        QS = QualtricsStats('exampleSurvey.xml', csv_lines_repetitor())

        start = time.time()
        json_output = QS.run()
        self.assertLess(time.time() - start, 20)

        res = json.loads(json_output)

        with open('edX_test.json') as f:
            ref = json.load(f)

        for n, stat in enumerate(res['statistics']):
            if 'average' in stat:
                self.assertAlmostEqual(stat['average'], ref['statistics'][n]['average'])
                stat['average'] = ref['statistics'][n]['average'] = 1

        self.assertEqual(res, ref)
