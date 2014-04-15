#!/usr/bin/env python3.3
#-*- coding:utf-8 -*-

class AbstractRunningAverage():
    """
    Stores a average value without the need to sum all the values together,
    or to keep them in memory at the same time.
    """
    def __init__(self):
        self._average = 0.0
        self._count = 0

    @property
    def average(self):
        """Get the current average."""
        return self._average

    @property
    def count(self):
        """Get the number of averaged values."""
        return self._count

class AdaptiveRunningAverage(AbstractRunningAverage):
    def add(self, value):
        self._average = self._average * (self._count / (self._count + 1)) + \
            (value / (self._count + 1))
        self._count += 1

class DiffRunningAverage(AbstractRunningAverage):
    # This one is slightly faster and simpler
    def add(self, value):
        self._count += 1
        self._average += (value - self._average) / self._count

RunningAverage = DiffRunningAverage

def test():
    import random
    import time

    print('Generating random values...')
    random.seed('running_average_42')  # to make the test deterministic
    values = [random.randint(0, 10) for _ in range(10000000)]

    print('Averaging...')
    true_avg = float(sum(values))/len(values)

    print('Testing...')

    A = AdaptiveRunningAverage()
    start = time.time()
    for v in values:
        A.add(v)
    stop = time.time()

    print('AdaptiveRunningAverage: {} seconds, {} error'.format(stop - start, A.average - true_avg))

    B = DiffRunningAverage()
    start = time.time()
    for v in values:
        B.add(v)
    stop = time.time()

    print('DiffRunningAverage: {} seconds, {} error'.format(stop - start, B.average - true_avg))

if __name__ == '__main__':
    test()
