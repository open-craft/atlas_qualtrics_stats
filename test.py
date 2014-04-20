import unittest
import random
import pep8


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
